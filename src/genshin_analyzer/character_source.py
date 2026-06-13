from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from genshin_analyzer.config import DEFAULT_CACHE_DIR, GENSHIN_DB_API_BASE_URL
from genshin_analyzer.exceptions import CharacterDataError


class GenshinDbCharacterClient:
    def __init__(
        self,
        base_url: str = GENSHIN_DB_API_BASE_URL,
        timeout: float = 30.0,
        user_agent: str = "GenshinAnalyzer/0.1.0",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=timeout, headers={"User-Agent": user_agent})

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> GenshinDbCharacterClient:
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()

    def list_character_names(self, language: str = "chinese") -> list[str]:
        payload = self._get(
            "/characters",
            {
                "query": "names",
                "matchCategories": "true",
                "resultLanguage": language,
            },
        )
        if not isinstance(payload, list):
            raise CharacterDataError("角色名称列表返回格式不正确。")
        return [str(item) for item in payload]

    def list_weapon_names(self, language: str = "chinese") -> list[str]:
        payload = self._get(
            "/weapons",
            {
                "query": "names",
                "matchCategories": "true",
                "resultLanguage": language,
            },
        )
        if not isinstance(payload, list):
            raise CharacterDataError("武器名称列表返回格式不正确。")
        return [str(item) for item in payload]

    def list_weapon_payloads(self, language: str = "chinese") -> list[dict[str, Any]]:
        payload = self._get(
            "/weapons",
            {
                "query": "names",
                "matchCategories": "true",
                "verboseCategories": "true",
                "resultLanguage": language,
            },
        )
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise CharacterDataError("武器列表详情返回格式不正确。")
        return payload

    def list_artifact_payloads(self, language: str = "chinese") -> list[dict[str, Any]]:
        payload = self._get(
            "/artifacts",
            {
                "query": "names",
                "matchCategories": "true",
                "verboseCategories": "true",
                "resultLanguage": language,
            },
        )
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise CharacterDataError("圣遗物列表详情返回格式不正确。")
        return payload

    def fetch_character(self, name: str, language: str = "chinese") -> dict[str, Any]:
        return self._fetch_folder("characters", name, language)

    def fetch_weapon(self, name: str, language: str = "chinese") -> dict[str, Any]:
        return self._fetch_folder("weapons", name, language)

    def fetch_talents(self, name: str, language: str = "chinese") -> dict[str, Any]:
        return self._fetch_folder("talents", name, language)

    def fetch_constellations(self, name: str, language: str = "chinese") -> dict[str, Any]:
        return self._fetch_folder("constellations", name, language)

    def fetch_stats(self, name: str, language: str = "chinese") -> dict[str, Any]:
        payload = self._get(
            "/stats",
            {
                "folder": "characters",
                "query": name,
                "queryLanguages": language,
                "resultLanguage": language,
            },
        )
        if not isinstance(payload, dict) or not payload:
            raise CharacterDataError(f"角色 {name} 的等级面板为空。")
        return payload

    def fetch_weapon_stats(self, name: str, language: str = "chinese") -> dict[str, Any]:
        payload = self._get(
            "/stats",
            {
                "folder": "weapons",
                "query": name,
                "queryLanguages": language,
                "resultLanguage": language,
            },
        )
        if not isinstance(payload, dict) or not payload:
            raise CharacterDataError(f"武器 {name} 的等级面板为空。")
        return payload

    def _fetch_folder(self, folder: str, name: str, language: str) -> dict[str, Any]:
        payload = self._get(
            f"/{folder}",
            {
                "query": name,
                "dumpResult": "true",
                "queryLanguages": language,
                "resultLanguage": language,
            },
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("result"), dict):
            raise CharacterDataError(f"角色 {name} 的 {folder} 数据返回格式不正确。")
        return payload

    def _get(self, path: str, params: dict[str, str]) -> Any:
        try:
            response = self.client.get(f"{self.base_url}{path}", params=params)
        except httpx.HTTPError as exc:
            raise CharacterDataError(f"无法连接 genshin-db-api：{exc}") from exc
        if response.status_code >= 400:
            raise CharacterDataError(
                f"genshin-db-api 请求失败：HTTP {response.status_code}，{response.text[:200]}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise CharacterDataError("genshin-db-api 返回了无效 JSON。") from exc


def write_character_cache(
    name: str,
    section: str,
    payload: dict[str, Any],
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> Path:
    target_dir = cache_dir / safe_filename(name)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{section}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in value)
