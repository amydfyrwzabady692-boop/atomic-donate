from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .engine import biggest_donor, match_condition, paid_qs, serialize_donation, totals
from .models import AlertCondition, Donation, SiteSettings


def _media(file_field) -> str:
    return file_field.url if file_field else ""


def _gif_urls(site: SiteSettings) -> list[str]:
    urls = []
    if site.alert_gif:
        urls.append(_media(site.alert_gif))
    for cond in AlertCondition.objects.all():
        if cond.gif:
            urls.append(_media(cond.gif))
    seen = set()
    unique = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def overlay_config(site: SiteSettings) -> dict:
    return {
        "gif": _media(site.alert_gif),
        "gifs": _gif_urls(site),
        "sound": _media(site.alert_sound),
        "sound_enabled": site.sound_enabled,
        "duration": site.alert_seconds,
        "tts": site.tts_enabled,
        "alert_volume": site.alert_volume / 100,
        "tts_volume": site.tts_volume / 100,
        "tts_rate": site.tts_rate,
        "tts_pitch": site.tts_pitch,
        "alert_style": site.alert_style,
        "list_style": site.list_style,
        "goal_style": site.goal_style,
        "accent": site.accent_color,
        "list_size": site.list_size,
        "goal": {
            "title": site.goal_title,
            "current": site.goal_current(),
            "target": site.goal_target_toman,
            "percent": site.goal_percent(),
            "active": site.goal_active,
            "show_title": site.goal_show_title,
            "show_details": site.goal_show_details,
            "fill": site.goal_fill,
            "track": site.goal_track,
            "text": site.goal_text,
            "bg": site.goal_bg,
            "radius": site.goal_radius,
            "font_size": site.goal_font_size,
            "bar_height": site.goal_bar_height,
            "title_tpl": site.goal_title_tpl,
            "details_tpl": site.goal_details_tpl,
        },
        "alert_text": site.alert_text,
        "alert_name_size": site.alert_name_size,
        "list_bg": site.list_bg,
        "list_text": site.list_text,
        "totals": totals(),
        "biggest_donor": biggest_donor("all"),
        "biggest_donor_week": biggest_donor("week"),
        "biggest_donor_month": biggest_donor("month"),
    }


def attach_alert_media(payload: dict, donation: Donation, site: SiteSettings) -> dict:
    payload["gif"] = _media(site.alert_gif)
    payload["sound"] = _media(site.alert_sound)
    payload["duration"] = site.alert_seconds
    payload["alert_style"] = site.alert_style
    cond = match_condition(donation.amount_toman)
    if cond:
        if cond.gif:
            payload["gif"] = _media(cond.gif)
        if cond.sound:
            payload["sound"] = _media(cond.sound)
        payload["duration"] = cond.duration
        if cond.style:
            payload["alert_style"] = cond.style
    return payload


def donation_payload(donation: Donation, site: SiteSettings) -> dict:
    payload = overlay_config(site)
    payload.update(serialize_donation(donation, site))
    attach_alert_media(payload, donation, site)
    payload["type"] = "donation"
    return payload


def snapshot_payload(site: SiteSettings) -> dict:
    limit = max(1, min(50, site.list_size))
    donors = [serialize_donation(d, site) for d in paid_qs().order_by("-paid_at", "-created_at")[:limit]]
    biggest = paid_qs().order_by("-amount_toman", "-paid_at").first()
    latest_visible = (
        Donation.objects.filter(status__in=[Donation.Status.PAID, Donation.Status.TEST])
        .order_by("-paid_at", "-created_at")
        .first()
    )
    latest = serialize_donation(latest_visible, site) if latest_visible else None
    if latest_visible and latest:
        attach_alert_media(latest, latest_visible, site)
    payload = overlay_config(site)
    payload.update(
        {
            "type": "snapshot",
            "donors": donors,
            "biggest": serialize_donation(biggest, site) if biggest else None,
            "latest": latest,
            "top": serialize_donation(biggest, site) if biggest else None,
        }
    )
    return payload


def settings_payload(site: SiteSettings) -> dict:
    payload = overlay_config(site)
    payload["type"] = "settings"
    return payload


def _send(payload: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)("overlays", {"type": "donation.event", "payload": payload})


def broadcast_donation(donation: Donation, site: SiteSettings | None = None) -> None:
    site = site or SiteSettings.load()
    payload = donation_payload(donation, site)
    if payload.get("skip_stream"):
        return
    _send(payload)


def broadcast_skip() -> None:
    _send({"type": "skip"})


def broadcast_settings(site: SiteSettings | None = None) -> None:
    _send(settings_payload(site or SiteSettings.load()))
