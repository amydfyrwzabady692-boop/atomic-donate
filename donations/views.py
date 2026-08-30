from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import AlertCondition, Donation, SiteSettings
from .realtime import broadcast_donation, broadcast_settings, broadcast_skip, snapshot_payload
from .zarinpal import ZARINPAL_MAX_TOMAN, ZARINPAL_MIN_TOMAN, ZarinPalError, payment_redirect_url, request_payment, verify_payment


def _overlay_ok(request) -> bool:
    expected = settings.OVERLAY_TOKEN
    if not expected:
        return True
    got = request.GET.get("key") or request.POST.get("key") or request.headers.get("X-Overlay-Key", "")
    return got == expected


def _overlay_guard(request):
    if not _overlay_ok(request):
        raise Http404("overlay key invalid")


def _overlay_urls():
    token = settings.OVERLAY_TOKEN
    suffix = f"?key={token}" if token else ""
    joiner = "&" if suffix else "?"
    base = settings.PUBLIC_BASE_URL.rstrip("/")

    def u(path, extra=""):
        url = f"{base}{path}{suffix}"
        return f"{url}{joiner}{extra}" if extra else url

    return {
        "alert": u("/overlay/alert/"),
        "list": u("/overlay/list/", "mode=last"),
        "list_biggest": u("/overlay/list/", "mode=biggest"),
        "list_donors": u("/overlay/list/", "mode=donors"),
        "goal": u("/overlay/goal/"),
        "latest": u("/overlay/label/", "mode=latest"),
        "biggest": u("/overlay/label/", "mode=biggest"),
        "donor": u("/overlay/label/", "mode=donor"),
        "total_day": u("/overlay/total/", "period=day"),
        "total_week": u("/overlay/total/", "period=week"),
        "total_month": u("/overlay/total/", "period=month"),
        "total_all": u("/overlay/total/", "period=all"),
        "queue": u("/overlay/queue/"),
        "timer": u("/overlay/timer/", "mode=countdown&seconds=3600"),
        "stopwatch": u("/overlay/timer/", "mode=stopwatch"),
        "top": u("/overlay/label/", "mode=biggest"),
        "dock": u("/panel/stream/"),
        "gateway": f"{base}/",
    }


def _int(value, default, min_v=0, max_v=10**12):
    try:
        parsed = int(str(value or "").replace(",", "").replace("،", "").strip())
    except ValueError:
        parsed = default
    return max(min_v, min(max_v, parsed))


def _panel_ctx(**extra):
    site = SiteSettings.load()
    host = settings.PUBLIC_BASE_URL.rstrip("/").replace("https://", "").replace("http://", "")
    ctx = {
        "site": site,
        "overlay_urls": _overlay_urls(),
        "merchant_ready": bool(settings.ZARINPAL_MERCHANT_ID),
        "public_host": host or "127.0.0.1:8000",
        "tool_pages": [
            "panel_alert",
            "panel_goal",
            "panel_conditions",
            "panel_censor",
            "panel_recap",
            "panel_widget",
            "panel_timer",
        ],
        "nav": [
            ("panel", "داشبورد", "grid"),
            ("panel_donations", "حمایت‌ها", "heart"),
            ("panel_gateway", "درگاه حمایت شما", "link"),
            ("panel_tools", "ابزارها", "obs"),
            ("panel_files", "فایل‌ها", "files"),
            ("panel_stream", "کنترل پنل استریم", "live"),
            ("panel_settings", "تنظیمات", "cog"),
        ],
    }
    ctx.update(extra)
    return ctx


def _amount_bounds(site):
    min_amt = max(ZARINPAL_MIN_TOMAN, site.min_amount_toman)
    stored_max = site.max_amount_toman
    if stored_max == 50_000_000:
        stored_max = ZARINPAL_MAX_TOMAN
    max_amt = min(ZARINPAL_MAX_TOMAN, max(min_amt, stored_max))
    return min_amt, max_amt


def donate_page(request):
    return render(request, "donate.html", _donate_ctx(SiteSettings.load()))


def _donate_ctx(site, errors=None, form=None):
    min_amt, max_amt = _amount_bounds(site)
    return {
        "site": site,
        "presets": site.presets(),
        "recent": Donation.objects.filter(status=Donation.Status.PAID, is_test=False, show_in_list=True)[: site.list_size],
        "emojis": site.emojis(),
        "errors": errors or [],
        "form": form,
        "min_amt": min_amt,
        "max_amt": max_amt,
    }


@require_POST
def start_payment(request):
    site = SiteSettings.load()
    name = (request.POST.get("name") or "").strip()[:64]
    message = (request.POST.get("message") or "").strip()[:280]
    emoji = (request.POST.get("emoji") or "").strip()[:16]
    if emoji and emoji not in site.emojis():
        emoji = ""
    amount = _int(request.POST.get("amount"), 0)
    min_amt, max_amt = _amount_bounds(site)

    errors = []
    if site.require_terms and request.POST.get("terms") != "on":
        errors.append("قوانین حمایت را بپذیر.")
    if len(name) < 2:
        errors.append("نام را وارد کن.")
    if amount < min_amt:
        errors.append(f"حداقل مبلغ {min_amt:,} تومان است.")
    if amount > max_amt:
        errors.append(f"حداکثر مبلغ {max_amt:,} تومان است (سقف زرین‌پال).")
    if errors:
        return render(request, "donate.html", _donate_ctx(site, errors, request.POST), status=400)

    donation = Donation.objects.create(
        name=name,
        amount_toman=amount,
        message=message,
        emoji=emoji,
        show_name=request.POST.get("show_name") == "on",
        show_message=request.POST.get("show_message") == "on",
        show_in_list=request.POST.get("show_in_list") == "on",
        status=Donation.Status.PENDING,
    )
    try:
        authority = request_payment(donation)
    except ZarinPalError as exc:
        donation.status = Donation.Status.FAILED
        donation.save(update_fields=["status"])
        return render(
            request,
            "result.html",
            {"ok": False, "site": site, "title": "پرداخت شروع نشد", "text": str(exc)},
            status=502,
        )

    donation.authority = authority
    donation.save(update_fields=["authority"])
    return redirect(payment_redirect_url(authority))


@require_GET
def zarinpal_callback(request):
    site = SiteSettings.load()
    status = request.GET.get("Status") or request.GET.get("status") or ""
    authority = request.GET.get("Authority") or request.GET.get("authority") or ""
    if status.upper() != "OK" or not authority:
        Donation.objects.filter(authority=authority).update(status=Donation.Status.FAILED)
        return render(
            request,
            "result.html",
            {"ok": False, "site": site, "title": "پرداخت لغو شد", "text": "تراکنش انجام نشد یا توسط شما لغو شد."},
        )

    donation = Donation.objects.filter(authority=authority).first()
    if donation is None:
        return HttpResponseBadRequest("تراکنش پیدا نشد.")

    if donation.status == Donation.Status.PAID:
        return render(
            request,
            "result.html",
            {"ok": True, "site": site, "donation": donation, "title": "حمایت ثبت شد", "text": "ممنون از حمایتت."},
        )

    try:
        data = verify_payment(donation)
    except ZarinPalError as exc:
        donation.status = Donation.Status.FAILED
        donation.save(update_fields=["status"])
        return render(
            request,
            "result.html",
            {"ok": False, "site": site, "title": "تأیید پرداخت ناموفق", "text": str(exc)},
        )

    donation.status = Donation.Status.PAID
    donation.ref_id = str(data.get("ref_id") or "")
    donation.paid_at = timezone.now()
    donation.save(update_fields=["status", "ref_id", "paid_at"])
    broadcast_donation(donation, site)
    return render(
        request,
        "result.html",
        {
            "ok": True,
            "site": site,
            "donation": donation,
            "title": "حمایت ثبت شد",
            "text": "ممنون از حمایتت. روی استریم نمایش داده می‌شود.",
        },
    )


def _overlay_page(request, template):
    _overlay_guard(request)
    site = SiteSettings.load()
    return render(
        request,
        template,
        {
            "overlay_key": request.GET.get("key", ""),
            "site": site,
            "mode": request.GET.get("mode", "last"),
            "period": request.GET.get("period", "all"),
        },
    )


def overlay_alert(request):
    return _overlay_page(request, "overlay/alert.html")


def overlay_list(request):
    return _overlay_page(request, "overlay/list.html")


def overlay_goal(request):
    return _overlay_page(request, "overlay/goal.html")


def overlay_top(request):
    return _overlay_page(request, "overlay/label.html")


def overlay_label(request):
    return _overlay_page(request, "overlay/label.html")


def overlay_total(request):
    return _overlay_page(request, "overlay/total.html")


def overlay_queue(request):
    return _overlay_page(request, "overlay/queue.html")


def overlay_timer(request):
    _overlay_guard(request)
    site = SiteSettings.load()
    return render(
        request,
        "overlay/timer.html",
        {
            "overlay_key": request.GET.get("key", ""),
            "site": site,
            "mode": request.GET.get("mode", "countdown"),
            "seconds": request.GET.get("seconds", "3600"),
        },
    )


@require_GET
def overlay_snapshot(request):
    _overlay_guard(request)
    return JsonResponse(snapshot_payload(SiteSettings.load()))


def panel_login(request):
    if request.user.is_authenticated:
        return redirect("panel")
    error = ""
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", ""),
            password=request.POST.get("password", ""),
        )
        if user is not None and user.is_staff:
            login(request, user)
            return redirect("panel")
        error = "نام کاربری یا رمز اشتباه است."
    return render(request, "panel/login.html", {"error": error})


@require_POST
@login_required
def panel_logout(request):
    logout(request)
    return redirect("panel_login")


@login_required
def panel_home(request):
    site = SiteSettings.load()
    since = timezone.now() - timedelta(days=14)
    paid = Donation.objects.filter(status=Donation.Status.PAID, is_test=False)
    month = paid.filter(paid_at__gte=timezone.now() - timedelta(days=30))
    daily = list(
        paid.filter(paid_at__gte=since)
        .annotate(day=TruncDate("paid_at"))
        .values("day")
        .annotate(total=Sum("amount_toman"), count=Count("id"))
        .order_by("day")
    )
    max_total = max((row["total"] or 0) for row in daily) if daily else 1
    chart = [
        {
            "label": row["day"].strftime("%m/%d") if row["day"] else "",
            "total": row["total"] or 0,
            "height": max(8, round((row["total"] or 0) * 100 / max_total)),
        }
        for row in daily
    ]
    return render(
        request,
        "panel/dashboard.html",
        _panel_ctx(
            stats={
                "month_sum": month.aggregate(total=Sum("amount_toman")).get("total") or 0,
                "month_count": month.count(),
                "all_sum": paid.aggregate(total=Sum("amount_toman")).get("total") or 0,
                "all_count": paid.count(),
                "goal_percent": site.goal_percent(),
            },
            donations=Donation.objects.all()[:8],
            chart=chart,
        ),
    )


@login_required
def panel_donations(request):
    qs = Donation.objects.all()
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(message__icontains=q) | Q(ref_id__icontains=q))
    return render(
        request,
        "panel/donations.html",
        _panel_ctx(donations=qs[:200], q=q),
    )


@login_required
def panel_gateway(request):
    site = SiteSettings.load()
    if request.method == "POST":
        site.display_name = (request.POST.get("display_name") or site.display_name)[:80]
        site.page_title = (request.POST.get("page_title") or site.page_title)[:120]
        site.bio = (request.POST.get("bio") or "")[:220]
        site.accent_color = (request.POST.get("accent_color") or site.accent_color)[:9]
        theme = request.POST.get("gateway_theme")
        if theme in dict(SiteSettings.GatewayTheme.choices):
            site.gateway_theme = theme
        site.show_goal_on_gateway = request.POST.get("show_goal_on_gateway") == "on"
        site.show_recent_on_gateway = request.POST.get("show_recent_on_gateway") == "on"
        site.min_amount_toman = max(ZARINPAL_MIN_TOMAN, _int(request.POST.get("min_amount_toman"), site.min_amount_toman, ZARINPAL_MIN_TOMAN))
        site.max_amount_toman = min(
            ZARINPAL_MAX_TOMAN,
            max(site.min_amount_toman, _int(request.POST.get("max_amount_toman"), site.max_amount_toman, site.min_amount_toman)),
        )
        site.preset_amounts = (request.POST.get("preset_amounts") or site.preset_amounts)[:120]
        site.instagram = (request.POST.get("instagram") or "")[:160]
        site.telegram = (request.POST.get("telegram") or "")[:160]
        site.youtube = (request.POST.get("youtube") or "")[:160]
        site.require_terms = request.POST.get("require_terms") == "on"
        site.emoji_pack = (request.POST.get("emoji_pack") or site.emoji_pack)[:80]
        if request.FILES.get("avatar"):
            site.avatar = request.FILES["avatar"]
        if request.POST.get("clear_avatar") == "on":
            site.avatar = None
        site.save()
        messages.success(request, "ظاهر درگاه ذخیره شد.")
        return redirect("panel_gateway")
    return render(request, "panel/gateway.html", _panel_ctx(
        themes=SiteSettings.GatewayTheme.choices,
        zarinpal_min=ZARINPAL_MIN_TOMAN,
        zarinpal_max=ZARINPAL_MAX_TOMAN,
    ))


@login_required
def panel_tools(request):
    return render(request, "panel/tools.html", _panel_ctx())


@login_required
def panel_alert(request):
    site = SiteSettings.load()
    if request.method == "POST":
        site.alert_seconds = _int(request.POST.get("alert_seconds"), site.alert_seconds, 2, 30)
        site.alert_volume = _int(request.POST.get("alert_volume"), site.alert_volume, 0, 100)
        site.tts_volume = _int(request.POST.get("tts_volume"), site.tts_volume, 0, 100)
        site.tts_rate = max(0.5, min(2.0, float(request.POST.get("tts_rate") or site.tts_rate)))
        site.tts_pitch = max(0.0, min(2.0, float(request.POST.get("tts_pitch") or site.tts_pitch)))
        site.tts_enabled = request.POST.get("tts_enabled") == "on"
        site.sound_enabled = request.POST.get("sound_enabled") == "on"
        site.alert_text = (request.POST.get("alert_text") or site.alert_text)[:9]
        site.alert_name_size = _int(request.POST.get("alert_name_size"), site.alert_name_size, 12, 48)
        alert_style = request.POST.get("alert_style")
        if alert_style in dict(SiteSettings.AlertStyle.choices):
            site.alert_style = alert_style
        if request.FILES.get("alert_gif"):
            site.alert_gif = request.FILES["alert_gif"]
        if request.FILES.get("alert_sound"):
            site.alert_sound = request.FILES["alert_sound"]
        if request.POST.get("clear_gif") == "on":
            site.alert_gif = None
        if request.POST.get("clear_sound") == "on":
            site.alert_sound = None
        site.save()
        broadcast_settings(site)
        messages.success(request, "آلارم، گیف و صدا ذخیره شد و به OBS فرستاده شد.")
        return redirect("panel_alert")
    return render(
        request,
        "panel/alert.html",
        _panel_ctx(alert_styles=SiteSettings.AlertStyle.choices),
    )


@login_required
def panel_goal(request):
    site = SiteSettings.load()
    if request.method == "POST":
        if request.POST.get("reset_goal"):
            paid = (
                Donation.objects.filter(status=Donation.Status.PAID, is_test=False)
                .aggregate(total=Sum("amount_toman"))
                .get("total")
                or 0
            )
            site.goal_baseline_toman = int(paid) + int(site.goal_start_toman)
            site.save(update_fields=["goal_baseline_toman"])
            broadcast_settings(site)
            messages.success(request, "هدف ریست شد و نوار از صفر شروع می‌شود.")
            return redirect("panel_goal")
        site.goal_title = (request.POST.get("goal_title") or site.goal_title)[:120]
        site.goal_target_toman = _int(request.POST.get("goal_target_toman"), site.goal_target_toman, 1000)
        site.goal_start_toman = _int(request.POST.get("goal_start_toman"), site.goal_start_toman, 0)
        site.goal_active = request.POST.get("goal_active") == "on"
        site.goal_show_title = request.POST.get("goal_show_title") == "on"
        site.goal_show_details = request.POST.get("goal_show_details") == "on"
        site.show_goal_on_gateway = request.POST.get("show_goal_on_gateway") == "on"
        site.goal_fill = (request.POST.get("goal_fill") or site.goal_fill)[:9]
        site.goal_track = (request.POST.get("goal_track") or site.goal_track)[:9]
        site.goal_text = (request.POST.get("goal_text") or site.goal_text)[:9]
        site.goal_bg = (request.POST.get("goal_bg") or site.goal_bg)[:9]
        site.goal_radius = _int(request.POST.get("goal_radius"), site.goal_radius, 0, 40)
        site.goal_font_size = _int(request.POST.get("goal_font_size"), site.goal_font_size, 10, 40)
        site.goal_bar_height = _int(request.POST.get("goal_bar_height"), site.goal_bar_height, 8, 48)
        site.goal_title_tpl = (request.POST.get("goal_title_tpl") or site.goal_title_tpl)[:80]
        site.goal_details_tpl = (request.POST.get("goal_details_tpl") or site.goal_details_tpl)[:80]
        goal_style = request.POST.get("goal_style")
        if goal_style in dict(SiteSettings.GoalStyle.choices):
            site.goal_style = goal_style
        site.save()
        broadcast_settings(site)
        messages.success(request, "تنظیمات هدف ذخیره شد و روی استریم اعمال شد.")
        suffix = "?tab=look" if request.POST.get("goal_fill") else ""
        return redirect(reverse("panel_goal") + suffix)
    return render(
        request,
        "panel/goal.html",
        _panel_ctx(tab=request.GET.get("tab", "main"), goal_styles=SiteSettings.GoalStyle.choices),
    )


WIDGETS = {
    "list": ("لیست آخرین حمایت‌ها", "list", "لیست عمودی آخرین دونیت‌ها برای گوشه استریم."),
    "list_biggest": ("لیست بزرگ‌ترین حمایت‌ها", "list_biggest", "مرتب بر اساس مبلغ."),
    "list_donors": ("لیست بزرگ‌ترین حمایت‌کننده‌ها", "list_donors", "جمع مبلغ هر نفر."),
    "latest": ("آخرین حمایت", "latest", "برچسب آخرین حامی."),
    "biggest": ("بزرگ‌ترین حمایت", "biggest", "صاحب عنوان بزرگ‌ترین دونیت."),
    "donor": ("بزرگ‌ترین حمایت‌کننده", "donor", "کسی که در مجموع بیشتر حمایت کرده."),
    "total_day": ("جمع امروز", "total_day", "جمع حمایت‌های امروز."),
    "total_week": ("جمع هفته", "total_week", "جمع ۷ روز اخیر."),
    "total_month": ("جمع ماه", "total_month", "جمع ۳۰ روز اخیر."),
    "total_all": ("جمع کل", "total_all", "جمع همه حمایت‌های واقعی."),
    "queue": ("صف نوبتی حمایت‌ها", "queue", "هر چند ثانیه یکی از حمایت‌ها را نشان می‌دهد."),
}


@login_required
def panel_widget(request, slug):
    if slug not in WIDGETS:
        raise Http404()
    title, url_key, hint = WIDGETS[slug]
    site = SiteSettings.load()
    if request.method == "POST":
        list_style = request.POST.get("list_style")
        if list_style in dict(SiteSettings.ListStyle.choices):
            site.list_style = list_style
        site.list_bg = (request.POST.get("list_bg") or site.list_bg)[:9]
        site.list_text = (request.POST.get("list_text") or site.list_text)[:9]
        site.list_size = _int(request.POST.get("list_size"), site.list_size, 1, 50)
        site.save()
        broadcast_settings(site)
        messages.success(request, "ظاهر ویجت ذخیره شد.")
        return redirect("panel_widget", slug=slug)
    return render(
        request,
        "panel/widget.html",
        _panel_ctx(
            widget_title=title,
            widget_hint=hint,
            widget_url=_overlay_urls()[url_key],
            list_styles=SiteSettings.ListStyle.choices,
            slug=slug,
        ),
    )


@login_required
def panel_timer(request):
    return render(request, "panel/timer.html", _panel_ctx())


@login_required
def panel_files(request):
    site = SiteSettings.load()
    assets = []
    if site.avatar:
        assets.append(("آواتار", site.avatar.url, "gateway"))
    if site.alert_gif:
        assets.append(("گیف آلارم", site.alert_gif.url, "alert"))
    if site.alert_sound:
        assets.append(("صدای آلارم", site.alert_sound.url, "sound"))
    for cond in AlertCondition.objects.all():
        if cond.gif:
            assets.append((f"گیف شرط {cond.label or cond.min_toman}", cond.gif.url, "alert"))
        if cond.sound:
            assets.append((f"صدای شرط {cond.label or cond.min_toman}", cond.sound.url, "sound"))
    return render(request, "panel/files.html", _panel_ctx(assets=assets))


@login_required
def panel_settings(request):
    site = SiteSettings.load()
    if request.method == "POST":
        site.list_size = _int(request.POST.get("list_size"), site.list_size, 1, 50)
        site.save()
        broadcast_settings(site)
        messages.success(request, "تنظیمات ذخیره شد.")
        return redirect("panel_settings")
    return render(request, "panel/settings.html", _panel_ctx())


def _can_stream(request):
    return request.user.is_authenticated or _overlay_ok(request)


def panel_stream(request):
    if not _can_stream(request):
        return redirect("panel_login")
    return render(
        request,
        "panel/stream.html",
        _panel_ctx(
            donations=Donation.objects.exclude(status=Donation.Status.PENDING)[:12],
            overlay_key=request.GET.get("key", ""),
            dock=not request.user.is_authenticated,
        ),
    )


def _make_test(request):
    site = SiteSettings.load()
    name = (request.POST.get("name") or "حامی تست").strip()[:64]
    message = (request.POST.get("message") or "این یک آلارم تست است.").strip()[:280]
    emoji = (request.POST.get("emoji") or "🔥").strip()[:16]
    amount = _int(request.POST.get("amount"), 50_000, 1000)
    donation = Donation.objects.create(
        name=name,
        amount_toman=amount,
        message=message,
        emoji=emoji,
        status=Donation.Status.TEST,
        is_test=True,
        authority=f"test-{uuid4().hex}",
        paid_at=timezone.now(),
    )
    broadcast_donation(donation, site)
    return donation


@login_required
@require_POST
def panel_test(request):
    _make_test(request)
    messages.success(request, "آلارم تست روی OBS پخش شد.")
    allowed = {"panel", "panel_alert", "panel_stream", "panel_donations", "panel_goal", "panel_conditions"}
    next_url = request.POST.get("next") if request.POST.get("next") in allowed else "panel_alert"
    return redirect(next_url)


@csrf_exempt
@require_POST
def dock_test(request):
    if not _overlay_ok(request):
        return JsonResponse({"ok": False}, status=403)
    _make_test(request)
    key = request.POST.get("key") or request.GET.get("key") or ""
    return redirect(f"/panel/stream/?key={key}")


@login_required
@require_POST
def panel_skip(request):
    broadcast_skip()
    messages.success(request, "هشدار فعلی رد شد.")
    return redirect("panel_stream")


@csrf_exempt
@require_POST
def dock_skip(request):
    if not _overlay_ok(request):
        return JsonResponse({"ok": False}, status=403)
    broadcast_skip()
    key = request.POST.get("key") or request.GET.get("key") or ""
    return redirect(f"/panel/stream/?key={key}")


@login_required
@require_POST
def panel_replay(request, pk):
    donation = get_object_or_404(Donation, pk=pk)
    broadcast_donation(donation)
    messages.success(request, f"آلارم {donation.name} دوباره پخش شد.")
    allowed = {"panel", "panel_alert", "panel_stream", "panel_donations", "panel_goal", "panel_conditions"}
    next_url = request.POST.get("next") if request.POST.get("next") in allowed else "panel_donations"
    return redirect(next_url)


@login_required
@require_POST
def panel_live_volume(request):
    site = SiteSettings.load()
    site.alert_volume = _int(request.POST.get("alert_volume"), site.alert_volume, 0, 100)
    site.tts_volume = _int(request.POST.get("tts_volume"), site.tts_volume, 0, 100)
    site.save(update_fields=["alert_volume", "tts_volume"])
    broadcast_settings(site)
    return JsonResponse({"ok": True, "alert_volume": site.alert_volume, "tts_volume": site.tts_volume})


@csrf_exempt
@require_POST
def dock_volume(request):
    if not _overlay_ok(request):
        return JsonResponse({"ok": False}, status=403)
    site = SiteSettings.load()
    site.alert_volume = _int(request.POST.get("alert_volume"), site.alert_volume, 0, 100)
    site.tts_volume = _int(request.POST.get("tts_volume"), site.tts_volume, 0, 100)
    site.save(update_fields=["alert_volume", "tts_volume"])
    broadcast_settings(site)
    return JsonResponse({"ok": True})


@login_required
def panel_conditions(request):
    site = SiteSettings.load()
    if request.method == "POST":
        AlertCondition.objects.create(
            min_toman=_int(request.POST.get("min_toman"), 0),
            max_toman=_int(request.POST.get("max_toman"), 0),
            label=(request.POST.get("label") or "")[:40],
            duration=_int(request.POST.get("duration"), site.alert_seconds, 2, 30),
            style=request.POST.get("style") or "",
            gif=request.FILES.get("gif"),
            sound=request.FILES.get("sound"),
        )
        messages.success(request, "شرط آلارم اضافه شد. دونیت داخل این بازه گیف/صدای خودش را می‌گیرد.")
        return redirect("panel_conditions")
    return render(
        request,
        "panel/conditions.html",
        _panel_ctx(conditions=AlertCondition.objects.all(), alert_styles=SiteSettings.AlertStyle.choices),
    )


@login_required
@require_POST
def panel_condition_delete(request, pk):
    get_object_or_404(AlertCondition, pk=pk).delete()
    messages.success(request, "شرط حذف شد.")
    return redirect("panel_conditions")


@login_required
def panel_censor(request):
    site = SiteSettings.load()
    if request.method == "POST":
        site.censor_enabled = request.POST.get("censor_enabled") == "on"
        mode = request.POST.get("censor_mode")
        if mode in dict(SiteSettings.CensorMode.choices):
            site.censor_mode = mode
        site.censor_words = request.POST.get("censor_words") or ""
        site.save()
        broadcast_settings(site)
        messages.success(request, "تنظیم سانسور ذخیره شد.")
        return redirect("panel_censor")
    return render(request, "panel/censor.html", _panel_ctx(censor_modes=SiteSettings.CensorMode.choices))


@login_required
def panel_recap(request):
    from .engine import totals, biggest_donor, paid_qs

    paid = paid_qs()
    month = totals()["month"]
    return render(
        request,
        "panel/recap.html",
        _panel_ctx(
            recap={
                "day": totals()["day"],
                "week": totals()["week"],
                "month": month,
                "all": totals()["all"],
                "count_month": paid.filter(paid_at__gte=timezone.now() - timedelta(days=30)).count(),
                "count_all": paid.count(),
                "top": biggest_donor("month"),
            }
        ),
    )
