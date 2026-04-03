"""HOLY Products integration for Home Assistant."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_PRODUCT_TYPES,
    CONF_SCAN_INTERVAL,
    CONF_TAGS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import HolyProductsCoordinator

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HOLY Products from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    config = entry.options if entry.options else entry.data
    scan_interval = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    product_types_raw = config.get(CONF_PRODUCT_TYPES, "")
    product_types = [t.strip() for t in product_types_raw.split(",") if t.strip()] if product_types_raw else []

    tags_raw = config.get(CONF_TAGS, "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

    coordinator = HolyProductsCoordinator(
        hass,
        scan_interval=scan_interval,
        product_types=product_types,
        tags=tags,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
