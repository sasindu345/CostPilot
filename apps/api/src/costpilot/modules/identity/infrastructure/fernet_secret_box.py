from cryptography.fernet import Fernet, InvalidToken


class FernetSecretBox:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key)

    def seal(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def open(self, sealed: str, max_age_seconds: int | None = None) -> str | None:
        try:
            return self._fernet.decrypt(sealed, ttl=max_age_seconds).decode()
        except InvalidToken:
            return None
