"""Smoke test: all HA modules import against a real Home Assistant (runs in CI)."""

import importlib

import pytest

pytest.importorskip("homeassistant")

MODULES = [
    "api",
    "binary_sensor",
    "button",
    "config_flow",
    "diagnostics",
    "entity",
    "hub",
    "number",
    "select",
    "sensor",
    "switch",
]


@pytest.mark.parametrize("module", MODULES)
def test_import(module):
    importlib.import_module(f"custom_components.makerlink.{module}")


def test_translations_match_strings():
    import json
    from pathlib import Path

    base = Path(__file__).resolve().parents[1] / "custom_components" / "makerlink"
    strings = json.loads((base / "strings.json").read_text(encoding="utf-8"))
    for lang in ("en", "de"):
        data = json.loads((base / "translations" / f"{lang}.json").read_text(encoding="utf-8"))
        assert data.keys() == strings.keys()
