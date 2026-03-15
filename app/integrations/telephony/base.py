from abc import ABC, abstractmethod


class TelephonyProvider(ABC):
    @abstractmethod
    def verify_signature(self, url: str, params: dict, signature: str) -> bool:
        """Return True if the webhook signature is valid."""
