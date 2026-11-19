"""Vendor-neutral OTP delivery boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol
from urllib.request import Request, urlopen

from app.core.config import settings


class SmsDeliveryError(RuntimeError):
    pass


class SmsProvider(Protocol):
    def send_otp(self, mobile_e164: str, code: str, purpose: str) -> None: ...


class DisabledSmsProvider:
    def send_otp(self, mobile_e164: str, code: str, purpose: str) -> None:
        raise SmsDeliveryError("SMS verification is not configured.")
class ConsoleSmsProvider:
    """Development-only OTP delivery through the backend terminal."""

    def send_otp(self, mobile_e164: str, code: str, purpose: str) -> None:
        if settings.ENVIRONMENT != "development":
            raise SmsDeliveryError(
                "Console SMS provider is only allowed in development."
            )

        masked_mobile = (
            mobile_e164[:3] + "******" + mobile_e164[-2:]
            if len(mobile_e164) > 5
            else "******"
        )

        print("\n========== DUKAANPULSE DEV OTP ==========")
        print(f"Mobile: {masked_mobile}")
        print(f"Purpose: {purpose}")
        print(f"OTP: {code}")
        print("Expires: 5 minutes")
        print("=========================================\n")


class GenericHttpSmsProvider:
    """Adapter for an operations-configured SMS gateway."""

    def send_otp(self, mobile_e164: str, code: str, purpose: str) -> None:
        if not settings.SMS_HTTP_URL or not settings.SMS_HTTP_AUTHORIZATION:
            raise SmsDeliveryError("SMS verification is not configured.")
        message = f"Your DukaanPulse verification code is {code}. It expires in 5 minutes."
        request = Request(
            settings.SMS_HTTP_URL,
            data=json.dumps({"to": mobile_e164, "message": message, "purpose": purpose}).encode("utf-8"),
            headers={
                "Authorization": settings.SMS_HTTP_AUTHORIZATION,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                if not 200 <= response.status < 300:
                    raise SmsDeliveryError("SMS provider rejected the verification request.")
        except SmsDeliveryError:
            raise
        except Exception as exc:
            raise SmsDeliveryError("SMS provider is unavailable.") from exc


@dataclass
class FakeSmsProvider:
    deliveries: list[tuple[str, str, str]] = field(default_factory=list)

    def send_otp(self, mobile_e164: str, code: str, purpose: str) -> None:
        self.deliveries.append((mobile_e164, code, purpose))


def get_sms_provider() -> SmsProvider:
    if settings.SMS_PROVIDER == "console":
        if settings.ENVIRONMENT != "development":
            raise SmsDeliveryError(
                "Console SMS provider is only allowed in development."
            )
        return ConsoleSmsProvider()

    if settings.SMS_PROVIDER == "generic_http":
        return GenericHttpSmsProvider()

    return DisabledSmsProvider()
