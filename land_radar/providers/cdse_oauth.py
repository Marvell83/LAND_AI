from __future__ import annotations

import time
from typing import Any

import requests


TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
PROCESS_URL = "https://sh.dataspace.copernicus.eu/process/v1"


class CDSEAuthError(RuntimeError):
    pass


class CDSEProcessError(RuntimeError):
    pass


class CDSEProcessSession:
    """OAuth client-credentials session with reusable access tokens."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        session: requests.Session | None = None,
    ):
        if not client_id or not client_secret:
            raise ValueError("Copernicus client_id and client_secret are required")
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = session or requests.Session()
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    def access_token(self) -> str:
        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token

        try:
            response = self.session.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            token = payload.get("access_token")
            if not token:
                raise CDSEAuthError("OAuth response did not contain access_token")
            expires_in = float(payload.get("expires_in", 3600))
        except CDSEAuthError:
            raise
        except (requests.RequestException, ValueError) as exc:
            raise CDSEAuthError(f"Copernicus OAuth failed: {exc}") from exc

        self._access_token = str(token)
        self._expires_at = time.time() + max(60.0, expires_in)
        return self._access_token

    def process(
        self,
        payload: dict[str, Any],
        *,
        accept: str = "image/tiff",
        timeout: float = 60.0,
    ) -> bytes:
        token = self.access_token()
        try:
            response = self.session.post(
                PROCESS_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": accept,
                    "Content-Type": "application/json",
                },
                timeout=timeout,
            )
            response.raise_for_status()
            return response.content
        except requests.RequestException as exc:
            raise CDSEProcessError(f"Copernicus Process API failed: {exc}") from exc
