import pytest
from httpx import ASGITransport, AsyncClient
from love_reply_api.main import app


@pytest.mark.asyncio
async def test_health_uses_common_envelope_and_wire_case() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health", headers={"X-Request-Id": "req-test"})

    assert response.status_code == 200
    assert response.json() == {
        "code": "OK",
        "message": "success",
        "data": {"status": "ok", "version": "1.0.0"},
        "requestId": "req-test",
        "timestamp": response.json()["timestamp"],
    }
