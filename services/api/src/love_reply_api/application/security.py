from base64 import b32decode, urlsafe_b64encode
from datetime import datetime
from hashlib import sha1, sha256
from hmac import compare_digest
from hmac import new as new_hmac
from struct import pack

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from cryptography.fernet import Fernet, InvalidToken

from love_reply_api.application.errors import ApiError
from love_reply_api.config import Settings


class SecretCipher:
    def __init__(self, settings: Settings) -> None:
        key = sha256(settings.data_encryption_key.get_secret_value().encode("utf-8")).digest()
        self._cipher = Fernet(urlsafe_b64encode(key))

    def encrypt(self, value: str) -> str:
        return self._cipher.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        try:
            return self._cipher.decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise ApiError(
                status_code=503,
                code="ENCRYPTED_SECRET_UNAVAILABLE",
                message="An encrypted secret cannot be recovered.",
                retryable=False,
            ) from exc


class PasswordService:
    _hasher = PasswordHasher(time_cost=3, memory_cost=65_536, parallelism=4)
    _dummy_hash = _hasher.hash("not-a-real-administrator-password")

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str | None, password: str) -> bool:
        candidate_hash = password_hash or self._dummy_hash
        try:
            valid = self._hasher.verify(candidate_hash, password)
        except VerificationError:
            return False
        return valid and password_hash is not None


class TotpService:
    @staticmethod
    def counter(*, now: datetime, period_seconds: int) -> int:
        return int(now.timestamp()) // period_seconds

    @staticmethod
    def code(*, secret: str, counter: int, digits: int) -> str:
        normalized = secret.strip().replace(" ", "").upper()
        padding = "=" * ((8 - len(normalized) % 8) % 8)
        key = b32decode(normalized + padding, casefold=True)
        digest = new_hmac(key, pack(">Q", counter), sha1).digest()
        offset = digest[-1] & 0x0F
        binary = int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF
        return str(binary % (10**digits)).zfill(digits)

    def verify(
        self,
        *,
        secret: str,
        presented_code: str,
        now: datetime,
        period_seconds: int,
        digits: int,
        valid_window: int,
        minimum_counter: int | None,
    ) -> int | None:
        current = self.counter(now=now, period_seconds=period_seconds)
        for offset in range(-valid_window, valid_window + 1):
            candidate_counter = current + offset
            if minimum_counter is not None and candidate_counter <= minimum_counter:
                continue
            try:
                candidate = self.code(
                    secret=secret,
                    counter=candidate_counter,
                    digits=digits,
                )
            except (ValueError, TypeError):
                return None
            if compare_digest(candidate, presented_code):
                return candidate_counter
        return None
