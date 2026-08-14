from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.security.egress_policy import enforce_worker_http_egress

_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleOAuthCodeRejectedError(RuntimeError):
    """Google rejected the authorization code or OAuth request."""


class GoogleOAuthExchangeTimeoutError(RuntimeError):
    """Google did not complete the token exchange within the deadline."""


class GoogleOAuthExchangeProviderError(RuntimeError):
    """The provider response or outbound connection was unavailable or invalid."""


class GoogleOAuthExchangeBlockedError(RuntimeError):
    """Outbound policy blocked the Google token endpoint."""


@dataclass(frozen=True, slots=True)
class GoogleOAuthTokens:
    access_token: str
    refresh_token: str | None
    expires_in: int | None


async def exchange_google_authorization_code(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> GoogleOAuthTokens:
    allowed_url = enforce_worker_http_egress(_GOOGLE_TOKEN_URL, tool="google_oauth")
    if not allowed_url:
        raise GoogleOAuthExchangeBlockedError("Google OAuth egress is blocked")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                allowed_url,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise GoogleOAuthExchangeTimeoutError(
            "Google OAuth token exchange timed out"
        ) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 400:
            raise GoogleOAuthCodeRejectedError(
                "Google rejected the authorization code"
            ) from exc
        raise GoogleOAuthExchangeProviderError(
            "Google OAuth token endpoint failed"
        ) from exc
    except httpx.HTTPError as exc:
        raise GoogleOAuthExchangeProviderError(
            "Google OAuth token endpoint is unavailable"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise GoogleOAuthExchangeProviderError(
            "Google OAuth token response is not valid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise GoogleOAuthExchangeProviderError("Invalid Google OAuth token response")

    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise GoogleOAuthExchangeProviderError(
            "Google OAuth token response missing access_token"
        )
    refresh_value = payload.get("refresh_token")
    if refresh_value is not None and not isinstance(refresh_value, str):
        raise GoogleOAuthExchangeProviderError(
            "Google OAuth token response has invalid refresh_token"
        )
    expires_value = payload.get("expires_in")
    if expires_value is None:
        expires_in = None
    elif isinstance(expires_value, bool):
        raise GoogleOAuthExchangeProviderError(
            "Google OAuth token response has invalid expires_in"
        )
    else:
        try:
            expires_in = int(expires_value)
        except (TypeError, ValueError) as exc:
            raise GoogleOAuthExchangeProviderError(
                "Google OAuth token response has invalid expires_in"
            ) from exc
        if expires_in <= 0:
            raise GoogleOAuthExchangeProviderError(
                "Google OAuth token response has invalid expires_in"
            )

    return GoogleOAuthTokens(
        access_token=access_token,
        refresh_token=refresh_value or None,
        expires_in=expires_in,
    )
