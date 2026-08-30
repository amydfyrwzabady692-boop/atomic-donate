from django.conf import settings
from django.urls import reverse

import httpx


ZARINPAL_MIN_TOMAN = 10_000
ZARINPAL_MAX_TOMAN = 100_000_000


class ZarinPalError(Exception):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


def _api_root():
    if settings.ZARINPAL_SANDBOX:
        return "https://sandbox.zarinpal.com"
    return "https://api.zarinpal.com"


def _startpay_url(authority: str) -> str:
    host = "sandbox.zarinpal.com" if settings.ZARINPAL_SANDBOX else "www.zarinpal.com"
    return f"https://{host}/pg/StartPay/{authority}"


def toman_to_rial(amount_toman: int) -> int:
    return int(amount_toman) * 10


def request_payment(donation) -> str:
    merchant = settings.ZARINPAL_MERCHANT_ID
    if not merchant:
        raise ZarinPalError("مرچنت‌کد زرین‌پال در فایل .env تنظیم نشده است.")

    callback = f"{settings.PUBLIC_BASE_URL}{reverse('callback')}"
    payload = {
        "merchant_id": merchant,
        "amount": toman_to_rial(donation.amount_toman),
        "callback_url": callback,
        "description": f"حمایت از {donation.name}"[:250],
    }

    response = httpx.post(
        f"{_api_root()}/pg/v4/payment/request.json",
        json=payload,
        timeout=20,
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    body = response.json()
    data = body.get("data") or {}
    errors = body.get("errors") or {}
    if data.get("code") == 100 and data.get("authority"):
        return data["authority"]
    message = errors.get("message") or data.get("message") or "خطا در اتصال به زرین‌پال"
    raise ZarinPalError(message, errors.get("code") or data.get("code"))


def verify_payment(donation) -> dict:
    payload = {
        "merchant_id": settings.ZARINPAL_MERCHANT_ID,
        "amount": toman_to_rial(donation.amount_toman),
        "authority": donation.authority,
    }
    response = httpx.post(
        f"{_api_root()}/pg/v4/payment/verify.json",
        json=payload,
        timeout=20,
        headers={"accept": "application/json", "content-type": "application/json"},
    )
    body = response.json()
    data = body.get("data") or {}
    errors = body.get("errors") or {}
    code = data.get("code")
    if code in (100, 101):
        return data
    message = errors.get("message") or data.get("message") or "پرداخت تأیید نشد"
    raise ZarinPalError(message, errors.get("code") or code)


def payment_redirect_url(authority: str) -> str:
    return _startpay_url(authority)
