from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from .models import AlertCondition, Donation, SiteSettings


DEFAULT_ALERT_TIERS = [
    {"min_toman": 0, "max_toman": 199_999, "label": "۰ تا ۲۰۰ هزار", "duration": 8},
    {"min_toman": 200_000, "max_toman": 999_999, "label": "۲۰۰ هزار تا یک میلیون", "duration": 8},
    {"min_toman": 1_000_000, "max_toman": 0, "label": "یک میلیون به بالا", "duration": 10},
]


def ensure_default_alert_tiers():
    if AlertCondition.objects.exists():
        return
    AlertCondition.objects.bulk_create([AlertCondition(**row) for row in DEFAULT_ALERT_TIERS])


def list_tier(amount: int) -> str:
    n = int(amount or 0)
    if n >= 1_000_000:
        return "tier-hot"
    if n >= 200_000:
        return "tier-ice"
    return "tier-ash"


def list_band(amount: int) -> str:
    n = int(amount or 0)
    if n >= 1_000_000:
        return "hot"
    if n >= 200_000:
        return "ice"
    if n >= 10_000:
        return "ash"
    return ""


def insert_band_slot(slots: list, item: dict) -> list:
    """Keep two seats. A new donor takes #1 if they beat the leader, otherwise #2."""
    if not slots:
        return [item]
    first = slots[0]
    if int(item.get("amount") or 0) > int(first.get("amount") or 0):
        return [item, first]
    return [first, item]


def ranked_board(site: SiteSettings | None = None) -> list:
    bands = {"hot": [], "ice": [], "ash": []}
    rows = paid_qs().order_by("paid_at", "created_at", "id")
    for donation in rows.iterator():
        band = list_band(donation.amount_toman)
        if not band:
            continue
        bands[band] = insert_band_slot(bands[band], serialize_donation(donation, site))
    board = []
    for key in ("hot", "ice", "ash"):
        board.extend(bands[key])
    return board


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
    """Pick the tightest amount range that contains this donation, like Reymit tiers."""
    matches = []
    for cond in AlertCondition.objects.all():
        if amount < cond.min_toman:
            continue
        if cond.max_toman and amount > cond.max_toman:
            continue
        span = cond.max_toman - cond.min_toman if cond.max_toman else 10**12
        matches.append((span, -cond.min_toman, cond.pk, cond))
    if not matches:
        return None
    matches.sort()
    return matches[0][3]


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
