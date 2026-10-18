"""Test setup.

The core modules (const, mars_format, display, controller) do not import
Home Assistant. If HA is not installed (e.g. on Windows), register the
package without executing its __init__ so they can still be imported.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if importlib.util.find_spec("homeassistant") is None:
    cc = types.ModuleType("custom_components")
    cc.__path__ = [str(ROOT / "custom_components")]
    pkg = types.ModuleType("custom_components.makerlink")
    pkg.__path__ = [str(ROOT / "custom_components" / "makerlink")]
    sys.modules.setdefault("custom_components", cc)
    sys.modules.setdefault("custom_components.makerlink", pkg)
