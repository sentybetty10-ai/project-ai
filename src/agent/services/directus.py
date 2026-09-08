from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("gyntrans.services.directus")

DIRECTUS_URL: str = os.getenv("DIRECTUS_BASE_URL", "").rstrip("/")
DIRECTUS_TOKEN: str = os.getenv("DIRECTUS_TOKEN", "")


def _tls_verify() -> bool:
    """Verifikasi TLS. Default True (aman). Untuk dev dengan sertifikat belum valid,
    set HTTP_VERIFY_TLS=false di .env (sudah dikonfigurasi di .env dev)."""
    return os.getenv("HTTP_VERIFY_TLS", "true").strip().lower() in {"1", "true", "yes"}


def _build_client() -> httpx.Client:
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=30, keepalive_expiry=30.0)
    timeout = httpx.Timeout(connect=3.0, read=15.0, write=3.0, pool=5.0)
    headers = {"Authorization": f"Bearer {DIRECTUS_TOKEN}"} if DIRECTUS_TOKEN else {}
    return httpx.Client(
        base_url=DIRECTUS_URL,
        headers=headers,
        limits=limits,
        timeout=timeout,
        verify=_tls_verify(),
    )


class DirectusService:
    def __init__(self) -> None:
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = _build_client()
        return self._client

    @property
    def configured(self) -> bool:
        return bool(DIRECTUS_URL)

    def get_items(
        self,
        collection: str,
        filter_dict: dict[str, Any] | None = None,
        fields: list[str] | None = None,
        sort: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if not DIRECTUS_URL:
            logger.warning("DIRECTUS_BASE_URL belum dikonfigurasi di .env")
            return []

        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if fields:
            params["fields"] = ",".join(fields)
        if sort:
            params["sort"] = ",".join(sort)
        if filter_dict:
            params["filter"] = json.dumps(filter_dict)

        try:
            res = self.client.get(f"/items/{collection}", params=params)
            if res.status_code == 200:
                return res.json().get("data", []) or []
            logger.error("Directus [%s] HTTP %s: %s", collection, res.status_code, res.text[:300])
        except httpx.RequestError as e:
            logger.error("Directus network error [%s]: %s", collection, e)
        except Exception as e:
            logger.error("Directus error [%s]: %s", collection, e)

        return []

    def get_all_items(
        self,
        collection: str,
        *,
        fields: list[str] | None = None,
        batch_size: int = 500,
        hard_limit: int = 100_000,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        offset = 0
        while offset < hard_limit:
            batch = self.get_items(collection, fields=fields, limit=batch_size, offset=offset)
            if not batch:
                break
            out.extend(batch)
            if len(batch) < batch_size:
                break
            offset += batch_size
        else:
            logger.warning("Paginasi Directus %s berhenti di hard_limit %d", collection, hard_limit)
        return out


directus_service = DirectusService()
