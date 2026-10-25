from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Mapping


@dataclass(frozen=True)
class CDSECredentials:
    client_id: str
    client_secret: str
    source: str


def resolve_cdse_credentials(
    secrets: Mapping[str, Any] | None = None,
) -> CDSECredentials | None:
    """Resolve credentials without ever serializing or logging the secret."""
    env_id = os.getenv("CDSE_CLIENT_ID", "").strip()
    env_secret = os.getenv("CDSE_CLIENT_SECRET", "").strip()
    if env_id and env_secret:
        return CDSECredentials(env_id, env_secret, "environment")

    if secrets:
        flat_id = str(secrets.get("CDSE_CLIENT_ID", "") or "").strip()
        flat_secret = str(secrets.get("CDSE_CLIENT_SECRET", "") or "").strip()
        if flat_id and flat_secret:
            return CDSECredentials(flat_id, flat_secret, "streamlit_secrets")

        section = secrets.get("copernicus")
        if isinstance(section, Mapping):
            section_id = str(section.get("client_id", "") or "").strip()
            section_secret = str(section.get("client_secret", "") or "").strip()
            if section_id and section_secret:
                return CDSECredentials(section_id, section_secret, "streamlit_secrets_section")

    return None
