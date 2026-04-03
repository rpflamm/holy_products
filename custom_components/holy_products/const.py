"""Constants for the HOLY Products integration."""

DOMAIN = "holy_products"
API_BASE_URL = "https://de.holy.com/products.json"
DEFAULT_SCAN_INTERVAL = 300  # 5 Minuten
DEFAULT_PAGE_LIMIT = 250
CONF_SCAN_INTERVAL = "scan_interval"
CONF_PRODUCT_TYPES = "product_types"
CONF_TAGS = "tags"
CONF_NOTIFY_AVAILABLE = "notify_available"
EVENT_NEW_PRODUCT = "holy_products_new_product"
EVENT_PRODUCT_AVAILABLE = "holy_products_product_available"
