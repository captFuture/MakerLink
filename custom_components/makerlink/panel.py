"""Sidebar panel: serves frontend/makerlink-panel.js and registers the panel."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN, PANEL_STATIC_URL, PANEL_URL_PATH, PANEL_WEBCOMPONENT

FRONTEND_DIR = Path(__file__).parent / "frontend"


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the static files and the sidebar entry (visible for all users)."""
    integration = await async_get_integration(hass, DOMAIN)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_STATIC_URL, str(FRONTEND_DIR), cache_headers=False)]
    )
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_WEBCOMPONENT,
        sidebar_title="MakerLink",
        sidebar_icon="mdi:card-account-details-outline",
        # Version as cache buster: after an update the browser loads the new file.
        module_url=f"{PANEL_STATIC_URL}/makerlink-panel.js?v={integration.version}",
        require_admin=False,
        config={},
    )
