import asyncio

import httpx
import pytest

from consent_service.infrai_captcha import InfraiCaptcha, InfraiError


@pytest.mark.asyncio
async def test_business_rejection_is_read_from_envelope_before_status() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            400,
            json={
                "ok": False,
                "data": None,
                "error": {"code": "INPUT_REJECTED", "message": "token rejected"},
                "metadata": {},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        verifier = InfraiCaptcha("test-key", client)
        with pytest.raises(InfraiError) as caught:
            await verifier.verify("captcha-token", "commerce_consent_grant")

    assert caught.value.code == "INPUT_REJECTED"
    assert caught.value.status_code == 400


@pytest.mark.asyncio
async def test_rate_limit_honors_retry_after() -> None:
    calls = 0
    delays: list[float] = []

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "2"},
                json={"ok": False, "data": None, "error": {}, "metadata": {}},
            )
        return httpx.Response(
            200, json={"ok": True, "data": {"verified": True}, "error": None, "metadata": {}}
        )

    async def record_sleep(delay: float) -> None:
        delays.append(delay)
        await asyncio.sleep(0)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await InfraiCaptcha("test-key", client, record_sleep).verify(
            "captcha-token", "commerce_consent_grant"
        )

    assert result == {"verified": True}
    assert delays == [2.0]

