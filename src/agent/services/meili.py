from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("gyntrans.services.meili")

MEILI_URL: str = os.getenv("MEILISEARCH_URL", "").rstrip("/")
MEILI_KEY: str = os.getenv("MEILISEARCH_KEY", "")


def _tls_verify() -> bool:
    """Verifikasi TLS. Default False karena sertifikat server Meilisearch VPS GYNTRANS
    saat ini belum menyertakan subdomain meilisearch.gyntransrozaqtana.com pada SAN.
    Bisa diaktifkan dengan HTTP_VERIFY_TLS=true bila sertifikat server sudah diperbarui."""
    enabled = os.getenv("HTTP_VERIFY_TLS", "false").strip().lower() in {"1", "true", "yes"}
    if not enabled:
        try:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except ImportError:
            pass
    return enabled


@dataclass
class SearchResult:
    hits: list[dict[str, Any]] = field(default_factory=list)
    estimated_total: int = 0

    def __bool__(self) -> bool:
        return bool(self.hits)

    def __len__(self) -> int:
        return len(self.hits)


def _build_client() -> httpx.Client:
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=30.0)
    timeout = httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=10.0)
    headers = {"Authorization": f"Bearer {MEILI_KEY}"} if MEILI_KEY else {}
    return httpx.Client(
        base_url=MEILI_URL,
        headers=headers,
        limits=limits,
        timeout=timeout,
        verify=_tls_verify(),
    )


class MeilisearchService:
    def __init__(self) -> None:
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = _build_client()
        return self._client

    @property
    def configured(self) -> bool:
        return bool(MEILI_URL)

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response | None:
        if not MEILI_URL:
            logger.warning("MEILISEARCH_URL belum dikonfigurasi")
            return None

        for attempt in range(2):
            try:
                res = self.client.request(method, path, **kwargs)
                if res.status_code >= 400:
                    logger.error(
                        "Meilisearch %s %s -> HTTP %s: %s",
                        method,
                        path,
                        res.status_code,
                        res.text[:300],
                    )
                    return None
                return res
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                logger.warning("Meilisearch retry %d/2 (%s): %s", attempt + 1, path, e)
                time.sleep(0.3)
                self._client = _build_client()
            except Exception as e:
                logger.error("Meilisearch error (%s): %s", path, e)
                return None
        return None

    def search(
        self,
        index_name: str,
        query: str = "",
        *,
        matching_strategy: str = "last",
        attributes_to_search_on: list[str] | None = None,
        filter_expr: str | None = None,
        limit: int = 30,
        with_ranking_score: bool = False,
    ) -> SearchResult:
        payload: dict[str, Any] = {
            "q": query or "",
            "matchingStrategy": matching_strategy,
            "limit": limit,
        }
        if attributes_to_search_on:
            payload["attributesToSearchOn"] = attributes_to_search_on
        if filter_expr:
            payload["filter"] = filter_expr
        if with_ranking_score:
            payload["showRankingScore"] = True

        res = self._request("POST", f"/indexes/{index_name}/search", json=payload)
        if res is None:
            return SearchResult()

        body = res.json()
        hits = body.get("hits", []) or []
        estimated = body.get("estimatedTotalHits")
        return SearchResult(
            hits=hits,
            estimated_total=int(estimated if estimated is not None else len(hits)),
        )

    def get_documents(
        self,
        index_name: str,
        *,
        fields: list[str] | None = None,
        batch_size: int = 1000,
        hard_limit: int = 200_000,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        offset = 0
        while offset < hard_limit:
            params: dict[str, Any] = {"limit": batch_size, "offset": offset}
            if fields:
                params["fields"] = ",".join(fields)

            res = self._request("GET", f"/indexes/{index_name}/documents", params=params)
            if res is None:
                break

            batch = res.json().get("results", []) or []
            if not batch:
                break

            out.extend(batch)
            if len(batch) < batch_size:
                break
            offset += batch_size
        else:
            logger.warning("Paginasi %s berhenti di hard_limit %d", index_name, hard_limit)

        return out

    def get_synonyms(self, index_name: str) -> dict[str, list[str]]:
        res = self._request("GET", f"/indexes/{index_name}/settings/synonyms")
        if res is None:
            return {}
        data = res.json()
        return data if isinstance(data, dict) else {}


meili_service = MeilisearchService()
