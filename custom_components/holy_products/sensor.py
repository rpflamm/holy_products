"""Sensor platform for HOLY Products."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HolyProductsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HOLY Products sensors."""
    coordinator: HolyProductsCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        HolyProductsCountSensor(coordinator, entry),
        HolyProductsNewSensor(coordinator, entry),
    ]

    # Create per-product-type sensors
    if coordinator.data:
        product_types = {
            p.get("product_type", "")
            for p in coordinator.data.values()
            if p.get("product_type")
        }
        for pt in sorted(product_types):
            entities.append(HolyProductsTypeSensor(coordinator, entry, pt))

    async_add_entities(entities, update_before_add=False)


def _slugify(text: str) -> str:
    """Simple slugify for entity IDs."""
    return text.lower().replace(" ", "_").replace("-", "_")


def _parse_tags(raw: Any) -> list[str]:
    """Parse tags from string or list."""
    if isinstance(raw, str) and raw:
        return [t.strip() for t in raw.split(",") if t.strip()]
    if isinstance(raw, list):
        return raw
    return []


class HolyProductsCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing total product count."""

    _attr_icon = "mdi:package-variant-closed"

    def __init__(self, coordinator: HolyProductsCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_count"
        self._attr_name = "HOLY Products Count"

    @property
    def native_value(self) -> int:
        """Return total product count."""
        if self.coordinator.data:
            return len(self.coordinator.data)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        data = self.coordinator.data or {}
        type_counter: Counter[str] = Counter()
        tag_counter: Counter[str] = Counter()

        for p in data.values():
            pt = p.get("product_type", "")
            if pt:
                type_counter[pt] += 1
            for tag in _parse_tags(p.get("tags", "")):
                tag_counter[tag] += 1

        return {
            "product_types": dict(type_counter.most_common()),
            "tags": dict(tag_counter.most_common(50)),
            "last_updated": datetime.now().isoformat(),
            "new_products_count": len(self.coordinator.new_products),
        }


class HolyProductsNewSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing new products from last update."""

    _attr_icon = "mdi:new-box"

    def __init__(self, coordinator: HolyProductsCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_new"
        self._attr_name = "HOLY Products New"

    @property
    def native_value(self) -> int:
        """Return count of new products."""
        return len(self.coordinator.new_products)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return new products list."""
        return {"products": self.coordinator.new_products}


class HolyProductsTypeSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing product count per product type."""

    _attr_icon = "mdi:tag-outline"

    def __init__(
        self,
        coordinator: HolyProductsCoordinator,
        entry: ConfigEntry,
        product_type: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._product_type = product_type
        slug = _slugify(product_type)
        self._attr_unique_id = f"{entry.entry_id}_type_{slug}"
        self._attr_name = f"HOLY Products {product_type}"

    def _get_products(self) -> list[dict[str, Any]]:
        """Get products of this type."""
        if not self.coordinator.data:
            return []
        return [
            p for p in self.coordinator.data.values()
            if p.get("product_type", "") == self._product_type
        ]

    @property
    def native_value(self) -> int:
        """Return product count for this type."""
        return len(self._get_products())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return product list for this type."""
        products = self._get_products()
        summary = []
        for p in products:
            images = p.get("images", [])
            variants = p.get("variants", [])
            prices = [v.get("price") for v in variants if v.get("price") is not None]
            summary.append({
                "id": p.get("id"),
                "title": p.get("title", ""),
                "price": min(prices) if prices else None,
                "image_url": images[0].get("src", "") if images else "",
            })
        return {"products": summary}
