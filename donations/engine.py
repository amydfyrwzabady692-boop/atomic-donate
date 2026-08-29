from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from .models import AlertCondition, Donation, SiteSettings


def paid_qs():
    return Donation.objects.filter(status=Donation.Status.PAID, is_test=False, show_in_list=True)


def in_period(qs, period: str):
    now = timezone.now()
    if period == "day":
        return qs.filter(paid_at__date=now.date())
    if period == "week":
        return qs.filter(paid_at__gte=now - timedelta(days=7))
    if period == "month":
        return qs.filter(paid_at__gte=now - timedelta(days=30))
    return qs


def match_condition(amount: int) -> AlertCondition | None:
    for cond in AlertCondition.objects.order_by("-min_toman"):
        if amount < cond.min_toman:
            continue
        if cond.max_toman and amount > cond.max_toman:
            continue
        return cond
    return None


def censor_message(site: SiteSettings, text: str) -> tuple[str, bool]:
    """Returns (text, skip_stream)."""
    if not site.censor_enabled or not text:
        return text, False
    words = [w.strip() for w in site.censor_words.replace("\n", ",").split(",") if w.strip()]
    hit = any(word and word in text for word in words)
    if not hit:
        return text, False
    if site.censor_mode == SiteSettings.CensorMode.SKIP:
        return text, True
    out = text
    for word in words:
        out = out.replace(word, "***")
    return out, False


def serialize_donation(donation: Donation, site: SiteSettings | None = None) -> dict:
    message = donation.message if donation.show_message else ""
    skip = False
    if site:
        message, skip = censor_message(site, message)
    return {
        "id": donation.id,
        "name": donation.name if donation.show_name else "ناشناس",
        "amount": donation.amount_toman,
        "message": message,
        "emoji": donation.emoji,
        "is_test": donation.is_test,
        "show_in_list": donation.show_in_list,
        "skip_stream": skip,
    }


def biggest_donor(period="all"):
    rows = (
        in_period(paid_qs(), period)
        .values("name")
        .annotate(total=Sum("amount_toman"))
        .order_by("-total")
    )
    row = rows.first()
    if not row:
        return None
    return {"name": row["name"], "amount": row["total"], "emoji": "👑", "message": ""}


def totals():
    data = {}
    for period in ("day", "week", "month", "all"):
        data[period] = in_period(paid_qs(), period).aggregate(total=Sum("amount_toman")).get("total") or 0
    return data
