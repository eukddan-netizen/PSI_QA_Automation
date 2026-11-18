"""Catalog loader & pytest nodeid-to-hierarchy + TC_ID mapper."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
import yaml

from dashboard.config import APP_CATALOG_PATH, PROJECT_ROOT, SECURITY_CATALOG_PATH
from dashboard.models import CatalogTargetPreset

_TC_TAG_RE = re.compile(r"^\[((?:APP|SEC)-\d+(?:-\d+)*)\]\s*(.*)$")


class CatalogRegistry:
    """Loads app_checks and security_checks YAML catalogs and resolves nodeids into 3-tier trees."""

    def __init__(self) -> None:
        self.app_categories: list[dict[str, Any]] = []
        self.security_checks: list[dict[str, Any]] = []
        self._app_folder_map: dict[str, dict[str, Any]] = {}
        self._app_subfolder_map: dict[tuple[str, str], dict[str, Any]] = {}
        self._sec_folder_map: dict[str, dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        self.app_categories = []
        self.security_checks = []
        self._app_folder_map = {}
        self._app_subfolder_map = {}
        self._sec_folder_map = {}

        if APP_CATALOG_PATH.exists():
            data = yaml.safe_load(APP_CATALOG_PATH.read_text(encoding="utf-8")) or {}
            self.app_categories = data.get("app_checks", [])
            for cat in self.app_categories:
                folder = str(cat.get("folder", "")).strip()
                if folder:
                    self._app_folder_map[folder] = cat
                for sub in cat.get("subcategories", []) or []:
                    sub_folder = str(sub.get("folder", "")).strip()
                    if folder and sub_folder:
                        self._app_subfolder_map[(folder, sub_folder)] = sub

        if SECURITY_CATALOG_PATH.exists():
            data = yaml.safe_load(SECURITY_CATALOG_PATH.read_text(encoding="utf-8")) or {}
            self.security_checks = data.get("checks", [])
            for chk in self.security_checks:
                folder = str(chk.get("folder", "")).strip()
                if folder:
                    self._sec_folder_map[folder] = chk

    def get_catalog_overview(self) -> dict[str, Any]:
        """Returns catalog structure and quick run presets for the dashboard UI."""
        presets: list[CatalogTargetPreset] = [
            CatalogTargetPreset(
                id="app_all",
                label="app_checks 전체",
                domain="app_checks",
                markers="app_check",
                description="프로그램 자체 UI/기능 점검 전체 (트레이~설정)",
            ),
        ]
        for cat in self.app_categories:
            presets.append(
                CatalogTargetPreset(
                    id=cat.get("id", cat.get("folder", "")),
                    label=f"{cat.get('folder', '')} · {cat.get('title', '')}",
                    domain="app_checks",
                    markers=cat.get("marker"),
                    description=cat.get("description", ""),
                )
            )
        presets.extend(
            [
                CatalogTargetPreset(
                    id="sec_pilot",
                    label="보안점검 시범 (7, 14, 45번)",
                    domain="security_checks",
                    markers="check07 or check14 or check45",
                    description="시범 구현된 주요 보안점검 3종 실행",
                ),
                CatalogTargetPreset(
                    id="sec_tier_a",
                    label="보안점검 Tier A 전체",
                    domain="security_checks",
                    markers="tier_a",
                    description="OS 기본 설정만으로 자동화 가능한 Tier A 전체",
                ),
                CatalogTargetPreset(
                    id="all",
                    label="전체 테스트 (app + security)",
                    domain="all",
                    description="수집된 전체 QA 자동화 테스트 실행",
                ),
            ]
        )

        return {
            "domains": [
                {
                    "id": "app_checks",
                    "title": "프로그램 기능 점검 (app_checks)",
                    "categories": self.app_categories,
                },
                {
                    "id": "security_checks",
                    "title": "보안점검 항목 (security_checks)",
                    "checks": self.security_checks,
                },
            ],
            "presets": [p.model_dump() for p in presets],
        }

    def resolve_nodeid(
        self,
        nodeid: str,
        docstring: str = "",
        markers: list[str] | None = None,
    ) -> dict[str, Any]:
        """Maps a pytest nodeid into (domain, category, subcategory, tc_id, display_title)."""
        markers = markers or []
        raw_file_part, _, func_part = nodeid.partition("::")
        file_part = raw_file_part.replace("\\", "/")
        rel_path = file_part
        try:
            p = Path(file_part)
            if p.is_absolute():
                rel_path = p.relative_to(PROJECT_ROOT).as_posix()
        except Exception:
            pass

        parts = rel_path.split("/")
        # Strip class name if present (e.g., TestClass::test_func[param] -> test_func)
        leaf_part = func_part.split("::")[-1] if func_part else rel_path
        param_suffix = ""
        if "[" in leaf_part and leaf_part.endswith("]"):
            idx = leaf_part.index("[")
            func_name = leaf_part[:idx]
            raw_param = leaf_part[idx + 1 : -1]
            decoded_param = _decode_pytest_param(raw_param)
            param_suffix = f" [{decoded_param}]"
        else:
            func_name = leaf_part

        tc_id, clean_title = _extract_tc_and_title(func_name, docstring)

        # tests/app_checks/<cat_folder>/[<sub_folder>/]<file.py>
        if len(parts) >= 3 and parts[0] == "tests" and parts[1] == "app_checks":
            cat_folder = parts[2]
            cat_meta = self._app_folder_map.get(cat_folder, {})
            cat_id = cat_meta.get("id") or cat_folder
            cat_title = _format_folder_title(cat_folder, cat_meta.get("title"))

            sub_id: str | None = None
            sub_title: str | None = None
            if len(parts) >= 5:
                sub_folder = parts[3]
                sub_meta = self._app_subfolder_map.get((cat_folder, sub_folder), {})
                sub_id = sub_meta.get("id") or sub_folder
                sub_title = _format_folder_title(sub_folder, sub_meta.get("title"))

            if not tc_id:
                cat_num = _leading_num(cat_folder) or "00"
                sub_num = _leading_num(parts[3]) if len(parts) >= 5 else "00"
                seq_num = _leading_func_num(func_name) or "010"
                tc_id = f"APP-{cat_num}-{sub_num}-{seq_num}"

            return {
                "domain": "app_checks",
                "domain_title": "app_checks (프로그램 기능 점검)",
                "category_id": cat_id,
                "category_title": cat_title,
                "subcategory_id": sub_id,
                "subcategory_title": sub_title,
                "tc_id": f"{tc_id}{param_suffix}".strip(),
                "id": f"{func_name}{param_suffix}".strip(),
                "title": f"{clean_title}{param_suffix}".strip(),
            }

        # tests/security_checks/<check_XX_name>/<file.py>
        if len(parts) >= 3 and parts[0] == "tests" and parts[1] == "security_checks":
            chk_folder = parts[2]
            chk_meta = self._sec_folder_map.get(chk_folder, {})
            tier = chk_meta.get("tier")
            tier_group_id = f"tier_{str(tier).lower()}" if tier else "security_other"
            tier_group_title = f"Tier {tier} 보안점검" if tier else "기타 보안점검"
            chk_num = chk_meta.get("id")
            chk_id = f"check_{chk_num:02d}" if isinstance(chk_num, int) else chk_folder
            chk_title = chk_meta.get("title") or chk_folder

            if not tc_id:
                chk_code = f"{chk_num:02d}" if isinstance(chk_num, int) else (_leading_num(chk_folder) or "00")
                seq_match = re.match(r"^test_(\d+)_", func_name)
                seq_code = f"{int(seq_match.group(1)) * 10:03d}" if seq_match else "010"
                tc_id = f"SEC-{chk_code}-{seq_code}"

            return {
                "domain": "security_checks",
                "domain_title": "security_checks (보안점검 항목)",
                "category_id": tier_group_id,
                "category_title": tier_group_title,
                "subcategory_id": chk_id,
                "subcategory_title": chk_title,
                "tc_id": f"{tc_id}{param_suffix}".strip(),
                "id": f"{func_name}{param_suffix}".strip(),
                "title": f"{clean_title}{param_suffix}".strip(),
            }

        return {
            "domain": "other",
            "domain_title": "기타 테스트",
            "category_id": "misc",
            "category_title": parts[1] if len(parts) > 1 else "일반",
            "subcategory_id": None,
            "subcategory_title": None,
            "tc_id": tc_id or func_name,
            "id": f"{func_name}{param_suffix}".strip(),
            "title": f"{clean_title}{param_suffix}".strip(),
        }


def _leading_num(name: str) -> str | None:
    m = re.match(r"^(?:check_)?(\d+)_", name)
    return f"{int(m.group(1)):02d}" if m else None


def _leading_func_num(func_name: str) -> str | None:
    m = re.match(r"^test_(\d+)_", func_name)
    if m:
        return m.group(1).zfill(3)
    return None


def _format_folder_title(folder: str, catalog_title: str | None) -> str:
    prefix_match = re.match(r"^(\d+)_", folder)
    if catalog_title and prefix_match:
        return f"{prefix_match.group(1)}. {catalog_title}"
    if catalog_title:
        return catalog_title
    return folder


def _extract_tc_and_title(func_name: str, docstring: str) -> tuple[str, str]:
    """Extracts structured TC_ID (APP-.. / SEC-..) and clean Korean title."""
    tc_id = ""
    if docstring:
        for raw_line in docstring.strip().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("-") or line.startswith("="):
                continue
            m = _TC_TAG_RE.match(line)
            if m:
                tc_id = m.group(1).strip()
                rest = m.group(2).strip()
                if rest:
                    return tc_id, _trim_title(rest)
                continue
            # Strip legacy prefixes like [점검 01], [정상], [취약], [Row 9], [TC: ...]
            cleaned = re.sub(r"^\[[^\]]+\]\s*", "", line).strip()
            if cleaned:
                return tc_id, _trim_title(cleaned)

    # Fallback: turn test_010_중복실행_방지 -> 중복실행 방지
    readable = re.sub(r"^test_(?:\d+_)?", "", func_name).replace("_", " ").strip()
    return tc_id, readable or func_name


def _decode_pytest_param(raw_param: str) -> str:
    """Decodes pytest's ASCII-escaped non-ASCII parametrize ids (e.g. \\uba54\\uc778 -> 메인)."""
    if "\\u" not in raw_param and "\\x" not in raw_param:
        return raw_param
    try:
        return bytes(raw_param, "utf-8").decode("unicode_escape")
    except Exception:
        return raw_param


def _trim_title(text: str) -> str:
    return text[:87].rstrip() + "..." if len(text) > 90 else text


catalog_registry = CatalogRegistry()
