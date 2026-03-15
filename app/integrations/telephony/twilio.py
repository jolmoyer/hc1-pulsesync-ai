from twilio.request_validator import RequestValidator

from app.config import get_settings
from app.integrations.telephony.base import TelephonyProvider


class TwilioProvider(TelephonyProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self._validator = RequestValidator(settings.twilio_auth_token)

    def verify_signature(self, url: str, params: dict, signature: str) -> bool:
        return self._validator.validate(url, params, signature)
