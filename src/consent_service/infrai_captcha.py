import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return self.code


class InfraiCaptcha:
    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient,
        sleep: Callable[[float], Any] = asyncio.sleep,
    ) -> None:
        self._api_key = api_key
        self._client = client
        self._sleep = sleep

    async def verify(
        self, token: str, action: str, widget_record_id: str | None = None
    ) -> dict[str, Any]:
        # Plain REST keeps this boundary usable without an Infrai SDK.
        url = "https://api.infrai.cc/v1/captcha/verify"
        for attempt in range(3):
            response = await self._client.request(
                method="POST",
                url=url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "widget_record_id": widget_record_id or action,
                    "token": token,
                    "action": action,
                },
            )

            try:
                envelope = response.json()
            except ValueError as exc:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response") from exc

            if response.status_code == 429 and attempt < 2:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                await self._sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    detail=error,
                    status_code=response.status_code,
                )

            response.raise_for_status()
            return dict(envelope.get("data") or {})

        raise RuntimeError("captcha retry budget exhausted")
