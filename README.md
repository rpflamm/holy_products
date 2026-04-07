# HOLY Products – Home Assistant Custom Integration

A custom integration for [Home Assistant](https://www.home-assistant.io/) that periodically fetches products from the [HOLY](https://de.holy.com/) online shop and notifies you about new arrivals.

## Features

- **Automatic product polling** from `https://de.holy.com/products.json` with full pagination support
- **New product detection** – fires Home Assistant events whenever new products appear
- **Configurable polling interval** (default: 5 minutes)
- **Filter by product type or tags** to only track the categories you care about
- **Sensors** for total product count, per-product-type counts, and new products
- **Back-in-stock detection** – fires events when a previously unavailable product variant becomes available again
- **Notification throttling** – configurable delay (default: 24h) between notifications for the same product to prevent spam
- **Automation-ready** – use the `holy_products_new_product` and `holy_products_product_available` events to trigger notifications, scripts, or any HA action

## Installation

### HACS (recommended)

1. Open HACS in your Home Assistant instance.
2. Go to **Integrations** → **⋮** (top right) → **Custom repositories**.
3. Add this repository URL and select **Integration** as the category.
4. Search for "HOLY Products" and install it.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/holy_products` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**.
2. Search for **HOLY Products**.
3. Configure the following options:

| Option | Description | Default |
|---|---|---|
| **Scan Interval** | Polling interval in minutes | `5` |
| **Product Types** | Comma-separated list of product types to track (leave empty for all) | _(empty)_ |
| **Tags** | Comma-separated list of tags to filter by (leave empty for all) | _(empty)_ |
| **Notify Back in Stock** | Enable notifications when products become available again | `true` |
| **Notification Throttle** | Delay (in hours) between notifications for the same product (set to 0 to disable) | `24` |

All options can be changed later via **Options** on the integration card.

## Sensors

The integration creates the following sensors:

### `sensor.holy_products_count`

- **State**: Total number of products.
- **Attributes**:
  - `product_types` – Dictionary of product types with their counts.
  - `tags` – Dictionary of tags with their counts.
  - `last_updated` – Timestamp of the last successful fetch.
  - `new_products_count` – Number of new products detected in the last update.

### `sensor.holy_products_new`

- **State**: Number of new products found in the most recent update.
- **Attributes**:
  - `products` – List of new products with `id`, `title`, `product_type`, `tags`, `price`, `image_url`, and `url`.

### `sensor.holy_products_back_in_stock`

- **State**: Number of products that became available again in the most recent update.
- **Attributes**:
  - `products` – List of back-in-stock products with `product_id`, `title`, `product_type`, `tags`, `price`, `image_url`, `url`, `variant_id`, and `variant_title`.

### `sensor.holy_products_{product_type}`

One sensor per product type (e.g., `sensor.holy_products_energy_drink`).

- **State**: Number of products of that type.
- **Attributes**:
  - `products` – List of products with `id`, `title`, `price`, and `image_url`.

## Events

### `holy_products_new_product`

Fired for **each** newly detected product. The event payload contains:

```json
{
  "product_id": 12345,
  "title": "Energy Drink Mango",
  "handle": "energy-drink-mango",
  "product_type": "Energy Drink",
  "tags": ["New Arrival", "Bestseller"],
  "price": "2.99",
  "compare_at_price": "3.99",
  "image_url": "https://cdn.shopify.com/...",
  "url": "https://de.holy.com/products/energy-drink-mango",
  "variants_count": 3
}
```

### `holy_products_product_available`

Fired when a product variant changes from unavailable to available (back in stock). The event payload contains:

```json
{
  "product_id": 12345,
  "title": "Energy Drink Mango",
  "handle": "energy-drink-mango",
  "product_type": "Energy Drink",
  "tags": ["Bestseller"],
  "price": "2.99",
  "compare_at_price": "3.99",
  "image_url": "https://cdn.shopify.com/...",
  "url": "https://de.holy.com/products/energy-drink-mango",
  "variants_count": 3,
  "variant_id": 67890,
  "variant_title": "12-Pack"
}
```

> **Note:** On the first run after installation or restart, all products are loaded silently without firing events. Only products that appear in subsequent updates are treated as new. Variant availability is tracked from the first run onward – only transitions from unavailable to available trigger back-in-stock events.

## Automation Examples

### Notify on any new product

```yaml
automation:
  - alias: "Notify on new HOLY product"
    trigger:
      - platform: event
        event_type: holy_products_new_product
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "New HOLY Product!"
          message: "{{ trigger.event.data.title }} – {{ trigger.event.data.price }}€"
          data:
            image: "{{ trigger.event.data.image_url }}"
            url: "{{ trigger.event.data.url }}"
```

### Notify only for specific tags

```yaml
automation:
  - alias: "Notify on new HOLY bestseller"
    trigger:
      - platform: event
        event_type: holy_products_new_product
    condition:
      - condition: template
        value_template: "{{ 'Bestseller' in trigger.event.data.tags }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "New HOLY Bestseller!"
          message: "{{ trigger.event.data.title }}"
```

### Notify only for a specific product type

```yaml
automation:
  - alias: "Notify on new HOLY Energy Drink"
    trigger:
      - platform: event
        event_type: holy_products_new_product
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.product_type == 'Energy Drink' }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          message: "New Energy Drink: {{ trigger.event.data.title }}"
```

### Notify when a product is back in stock

```yaml
automation:
  - alias: "Notify on HOLY product back in stock"
    trigger:
      - platform: event
        event_type: holy_products_product_available
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Back in Stock!"
          message: "{{ trigger.event.data.title }} ({{ trigger.event.data.variant_title }}) is available again!"
          data:
            image: "{{ trigger.event.data.image_url }}"
            url: "{{ trigger.event.data.url }}"
```

## How It Works

1. The integration polls `https://de.holy.com/products.json` using pagination (`limit=250` per page).
2. All pages are fetched until a page returns fewer products than the limit.
3. Optional filters (product type, tags) are applied.
4. Product IDs are compared against the previously known set.
5. For each new product, a `holy_products_new_product` event is fired on the Home Assistant event bus.
6. Variant availability (`available` field) is tracked. When a variant changes from unavailable to available, a `holy_products_product_available` event is fired.
7. **Notification throttling**: Before firing an event for a product, the integration checks if the configured throttle period (default: 24h) has passed since the last notification for that specific product. This prevents duplicate alerts if a product quickly goes in and out of stock.
8. Sensor entities are updated with the latest data.

## API Details

The integration uses the public Shopify-based product API at `https://de.holy.com/products.json`. No API key or authentication is required.

- **Pagination**: `?limit=250&page=1`, incrementing `page` until fewer than `limit` products are returned.
- **Rate limiting**: Standard Shopify rate limits may apply. The default 5-minute interval keeps request frequency low.
- **Timeout**: Each HTTP request has a 30-second timeout.

## Development

### Code Quality

This project uses the following tools to ensure code quality:

- **[ruff](https://docs.astral.sh/ruff/)** – Linting and formatting (configured in `pyproject.toml`)
- **[mypy](https://mypy-lang.org/)** – Static type checking
- **[pre-commit](https://pre-commit.com/)** – Git hooks for automated checks

```bash
# Install dev dependencies
pip install ruff mypy pre-commit

# Set up pre-commit hooks
pre-commit install

# Run checks manually
ruff check custom_components/
ruff format --check custom_components/
mypy custom_components/
```

## Project Structure

```
custom_components/
  holy_products/
    __init__.py          # Integration setup (async_setup_entry)
    manifest.json        # Integration metadata
    config_flow.py       # Config flow & options flow (UI configuration)
    const.py             # Constants (domain, API URL, defaults)
    coordinator.py       # DataUpdateCoordinator (API fetching, pagination, new product & availability detection)
    sensor.py            # Sensor platform (product count, per-type, new products, back in stock)
    strings.json         # UI strings (English)
    translations/
      de.json            # UI strings (German)
```

## License

This project is provided as-is for personal use. Not affiliated with HOLY GmbH.
