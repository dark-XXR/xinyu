from collections.abc import Callable
from email.message import EmailMessage
from typing import Any

import pytest
from love_reply_api.application import provider_runtime
from love_reply_api.application.provider_runtime import SmtpTransport


class FakeSmtpClient:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.calls: list[tuple[str, object]] = []
        self.message: EmailMessage | None = None

    def __enter__(self) -> "FakeSmtpClient":
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def ehlo(self) -> None:
        self.calls.append(("ehlo", None))

    def starttls(self, *, context: object) -> None:
        self.calls.append(("starttls", context))

    def login(self, username: str, password: str) -> None:
        self.calls.append(("login", (username, password)))

    def send_message(self, message: EmailMessage) -> None:
        self.calls.append(("send_message", None))
        self.message = message


@pytest.mark.parametrize(
    ("tls_mode", "implicit", "expects_starttls"),
    [("STARTTLS", False, True), ("IMPLICIT", True, False)],
)
def test_smtp_transport_uses_authenticated_tls(
    monkeypatch: pytest.MonkeyPatch,
    tls_mode: str,
    implicit: bool,
    expects_starttls: bool,
) -> None:
    clients: list[FakeSmtpClient] = []

    def factory(**kwargs: Any) -> FakeSmtpClient:
        client = FakeSmtpClient(**kwargs)
        clients.append(client)
        return client

    def unused_factory(**kwargs: Any) -> FakeSmtpClient:
        raise AssertionError(f"unexpected SMTP constructor: {kwargs}")

    plain_factory: Callable[..., FakeSmtpClient] = unused_factory if implicit else factory
    ssl_factory: Callable[..., FakeSmtpClient] = factory if implicit else unused_factory
    monkeypatch.setattr(provider_runtime, "SMTP", plain_factory)
    monkeypatch.setattr(provider_runtime, "SMTP_SSL", ssl_factory)
    monkeypatch.setattr(provider_runtime, "create_default_context", lambda: "tls-context")

    SmtpTransport._send_sync(
        {
            "host": "smtp.example.com",
            "port": 465 if implicit else 587,
            "tlsMode": tls_mode,
            "senderName": "Love Reply",
            "senderAddress": "noreply@example.com",
            "replyToAddress": "support@example.com",
            "timeoutMs": 10000,
        },
        {"username": "smtp-user", "password": "smtp-password"},
        "recipient@example.com",
        "Login code",
        "Your code is 123456.",
        "<p>Your code is <strong>123456</strong>.</p>",
    )

    assert len(clients) == 1
    client = clients[0]
    assert ("login", ("smtp-user", "smtp-password")) in client.calls
    assert any(name == "starttls" for name, _ in client.calls) is expects_starttls
    assert client.message is not None
    assert client.message["To"] == "recipient@example.com"
    assert client.message["Reply-To"] == "support@example.com"
    assert "123456" in client.message.as_string()
