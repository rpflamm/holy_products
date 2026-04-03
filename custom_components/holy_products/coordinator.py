"""DataUpdateCoordinator for HOLY Products."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_BASE_URL, DEFAULT_PAGE_LIMIT, EVENT_NEW_PRODUCT

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


class HolyProductsCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Coordinator to fetch HOLY products with pagination and new-product detection."""

    def __init__(
        self,
        hass: HomeAssistant,
        scan_interval: int,
        product_types: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="HOLY Products",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._product_types = product_types or []
        self._tags = tags or []
        self._known_product_ids: set[int] = set()
        self._first_run = True
        self.new_products: list[dict[str, Any]] = []

    async def _fetch_all_products(self) -> list[dict[str, Any]]:
        """Fetch all products with pagination."""
        session = async_get_clientsession(self.hass)
        all_products: list[dict[str, Any]] = []
        page = 1
        limit = DEFAULT_PAGE_LIMIT

        while True:
            url = f"{API_BASE_URL}?limit={limit}&page={page}"
            try:
                async with asyncio.timeout(REQUEST_TIMEOUT):
                    resp = await session.get(url)
                    resp.raise_for_status()
                    data = await resp.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                raise UpdateFailed(f"Error fetching page {page}: {err}") from err

            products = data.get("products", [])
            if not products:
                break

            all_products.extend(products)
            _LOGGER.debug("Fetched page %d with %d products", page, len(products))

            if len(products) < limit:
                break
            page += 1

        return all_products

    def _extract_product_event_data(self, product: dict[str, Any]) -> dict[str, Any]:
        """Extract event payload from a product."""
        variants = product.get("variants", [])
        prices = []
        compare_at_price = None
        for v in variants:
            price = v.get("price")
            if price is not None:
                prices.append(price)
            cap = v.get("compare_at_price")
            if cap is not None and compare_at_price is None:
                compare_at_price = cap

        images = product.get("images", [])
        image_url = images[0].get("src", "") if images else ""
        handle = product.get("handle", "")
        tags_raw = product.get("tags", "")
        tags_list = [t.strip() for t in tags_raw.split(",")] if isinstance(tags_raw, str) and tags_raw else tags_raw if isinstance(tags_raw, list) else []

        return {
            "product_id": product.get("id"),
            "title": product.get("title", ""),
            "handle": handle,
            "product_type": product.get("product_type", ""),
            "tags": tags_list,
            "price": min(prices) if prices else None,
            "compare_at_price": compare_at_price,
            "image_url": image_url,
            "url": f"https://de.holy.com/products/{handle}",
            "variants_count": len(variants),
        }

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        """Fetch products, detect new ones, fire events."""
        all_products = await self._fetch_all_products()

        # Apply filters
        filtered = all_products
        if self._product_types:
            pt_lower = [pt.lower() for pt in self._product_types]
            filtered = [p for p in filtered if p.get("product_type", "").lower() in pt_lower]
        if self._tags:
            tags_lower = {t.lower() for t in self._tags}
            def has_tag(p: dict) -> bool:
                raw = p.get("tags", "")
                if isinstance(raw, str):
                    ptags = {t.strip().lower() for t in raw.split(",") if t.strip()}
                elif isinstance(raw, list):
                    ptags = {t.lower() for t in raw}
                else:
                    ptags = set()
                return bool(ptags & tags_lower)
            filtered = [p for p in filtered if has_tag(p)]

        products_by_id: dict[int, dict[str, Any]] = {}
        for p in filtered:
            pid = p.get("id")
            if pid is not None:
                products_by_id[pid] = p

        # Detect new products
        current_ids = set(products_by_id.keys())
        self.new_products = []

        if self._first_run:
            self._first_run = False
            _LOGGER.info("Initial fetch: %d products loaded", len(products_by_id))
        else:
            new_ids = current_ids - self._known_product_ids
            if new_ids:
                _LOGGER.info("Detected %d new product(s)", len(new_ids))
                for pid in new_ids:
                    product = products_by_id[pid]
                    event_data = self._extract_product_event_data(product)
                    self.new_products.append(event_data)
                    self.hass.bus.async_fire(EVENT_NEW_PRODUCT, event_data)

        self._known_product_ids = current_ids
        return products_by_id
