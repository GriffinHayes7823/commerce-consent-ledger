import os
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .consent_ledger import CommerceScope, ConsentLedger
from .infrai_captcha import InfraiCaptcha, InfraiError


class GrantConsentRequest(BaseModel):
    user_id: str = Field(min_length=1)
    scopes: set[CommerceScope] = Field(min_length=1)
    captcha_token: str = Field(min_length=1)
    widget_record_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)


class RevokeConsentRequest(BaseModel):
    user_id: str = Field(min_length=1)
    scopes: set[CommerceScope] = Field(min_length=1)


class ConsentResponse(BaseModel):
    user_id: str
    active_scopes: list[CommerceScope]


class PermissionResponse(BaseModel):
    user_id: str
    scope: CommerceScope
    permitted: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("INFRAI_API_KEY is required")
    async with httpx.AsyncClient(timeout=10.0) as client:
        app.state.captcha = InfraiCaptcha(api_key, client)
        yield


app = FastAPI(title="Commerce consent", lifespan=lifespan)
app.state.ledger = ConsentLedger()


def ledger(request: Request) -> ConsentLedger:
    return request.app.state.ledger


def captcha(request: Request) -> InfraiCaptcha:
    return request.app.state.captcha


@app.exception_handler(InfraiError)
async def infrai_error_handler(_request: Request, exc: InfraiError) -> JSONResponse:
    client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
    return JSONResponse(
        status_code=client_status,
        content={"error": {"code": exc.code, "detail": exc.detail}},
    )


@app.post("/consents/grant", response_model=ConsentResponse)
async def grant_consent(
    body: GrantConsentRequest,
    store: Annotated[ConsentLedger, Depends(ledger)],
    captcha_client: Annotated[InfraiCaptcha, Depends(captcha)],
) -> ConsentResponse:
    await captcha_client.verify(
        body.captcha_token, "commerce_consent_grant", body.widget_record_id
    )
    try:
        store.grant(body.user_id, body.scopes, body.request_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ConsentResponse(
        user_id=body.user_id, active_scopes=sorted(store.active_scopes(body.user_id))
    )


@app.post("/consents/revoke", response_model=ConsentResponse)
async def revoke_consent(
    body: RevokeConsentRequest,
    store: Annotated[ConsentLedger, Depends(ledger)],
) -> ConsentResponse:
    active = store.revoke(body.user_id, body.scopes)
    return ConsentResponse(user_id=body.user_id, active_scopes=sorted(active))


@app.get("/consents/{user_id}/{scope}", response_model=PermissionResponse)
async def check_consent(
    user_id: str,
    scope: CommerceScope,
    store: Annotated[ConsentLedger, Depends(ledger)],
) -> PermissionResponse:
    return PermissionResponse(
        user_id=user_id, scope=scope, permitted=store.permits(user_id, scope)
    )
