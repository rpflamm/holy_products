# HOLY Products – Home Assistant Custom Integration

## Übersicht

Eine Custom Integration für Home Assistant, die regelmäßig Produkte von `https://de.holy.com/products.json` abfragt, als Sensoren bereitstellt und bei neuen Produkten Events feuert, auf die Automatisierungen reagieren können.

---

## 1. Projektstruktur

```
custom_components/
  holy_products/
    __init__.py          # Integration Setup (async_setup_entry)
    manifest.json        # Metadaten, Abhängigkeiten, Version
    config_flow.py       # Config Flow (UI-Konfiguration)
    const.py             # Konstanten (DOMAIN, DEFAULT_SCAN_INTERVAL, API_URL, …)
    coordinator.py       # DataUpdateCoordinator – zentrale Datenabfrage
    sensor.py            # Sensor-Plattform (Produkt-Sensoren)
    strings.json         # UI-Texte (EN)
    translations/
      de.json            # UI-Texte (DE)
```

---

## 2. Konstanten (`const.py`)

| Konstante | Wert |
|---|---|
| `DOMAIN` | `holy_products` |
| `API_BASE_URL` | `https://de.holy.com/products.json` |
| `DEFAULT_SCAN_INTERVAL` | `300` (5 Minuten) |
| `DEFAULT_PAGE_LIMIT` | `250` |
| `CONF_SCAN_INTERVAL` | `scan_interval` |
| `CONF_PRODUCT_TYPES` | `product_types` |
| `CONF_TAGS` | `tags` |

---

## 3. API-Abruf & Paginierung (`coordinator.py`)

### 3.1 Klasse `HolyProductsCoordinator(DataUpdateCoordinator)`

- Erbt von `homeassistant.helpers.update_coordinator.DataUpdateCoordinator`.
- `__init__`: Erhält `hass`, `scan_interval`, optional Filter (Tags, Product Types).
- `_async_update_data()`:
  1. Seite `page=1` mit `limit=250` abrufen (via `aiohttp` / `async_get_clientsession`).
  2. Solange `len(products) == limit` → nächste Seite abrufen.
  3. Alle Produkte in einer Liste zusammenführen.
  4. Neue Produkte erkennen: Vergleich der Produkt-IDs mit dem vorherigen Datensatz.
  5. Für jedes neue Produkt ein **Event** `holy_products_new_product` auf dem HA Event-Bus feuern mit Payload:
     - `product_id`, `title`, `handle`, `product_type`, `tags`, `price` (günstigste Variante), `image_url` (erstes Bild), `url` (`https://de.holy.com/products/{handle}`)
  6. Rückgabe: Dict mit allen Produkten, indexiert nach `id`.

### 3.2 Fehlerbehandlung

- `aiohttp.ClientError` → `UpdateFailed` werfen.
- Timeout von 30 Sekunden pro Request.
- Logging bei leeren Seiten / Fehlern.

---

## 4. Config Flow (`config_flow.py`)

### 4.1 Schritt 1: Basis-Konfiguration

- **Abfrageintervall** (int, Default: 5 Minuten, Min: 1 Minute)
- **Produkt-Typen filtern** (optional, Komma-getrennte Liste)
- **Tags filtern** (optional, Komma-getrennte Liste)

### 4.2 Options Flow

- Gleiche Felder wie Schritt 1, damit der Nutzer nachträglich ändern kann.
- Bei Änderung: Coordinator-Intervall aktualisieren und Daten neu laden.

---

## 5. Sensoren (`sensor.py`)

### 5.1 Haupt-Sensor: `sensor.holy_products_count`

- **State**: Anzahl aller abgerufenen Produkte.
- **Attribute**:
  - `product_types`: Liste aller vorhandenen Produkt-Typen mit Anzahl.
  - `tags`: Liste aller vorhandenen Tags mit Anzahl.
  - `last_updated`: Zeitstempel der letzten Abfrage.
  - `new_products_count`: Anzahl neuer Produkte seit letztem Update.

### 5.2 Sensor pro Produkt-Typ: `sensor.holy_products_{product_type}`

- **State**: Anzahl Produkte dieses Typs.
- **Attribute**:
  - `products`: Liste mit `id`, `title`, `price`, `image_url` der Produkte dieses Typs.

### 5.3 Sensor für neue Produkte: `sensor.holy_products_new`

- **State**: Anzahl neuer Produkte beim letzten Update.
- **Attribute**:
  - `products`: Liste der neuen Produkte (id, title, product_type, tags, price, image_url, url).

---

## 6. Events für Automatisierungen

### Event: `holy_products_new_product`

Wird für **jedes** neue Produkt einzeln gefeuert.

**Payload:**
```json
{
  "product_id": 12345,
  "title": "Energy Drink Mango",
  "handle": "energy-drink-mango",
  "product_type": "Energy Drink",
  "tags": ["Neueinsteiger", "Bestseller"],
  "price": "2.99",
  "compare_at_price": "3.99",
  "image_url": "https://cdn.shopify.com/...",
  "url": "https://de.holy.com/products/energy-drink-mango",
  "variants_count": 3
}
```

### Beispiel-Automatisierung (YAML)

```yaml
automation:
  - alias: "Benachrichtigung bei neuem HOLY Produkt"
    trigger:
      - platform: event
        event_type: holy_products_new_product
    condition:
      - condition: template
        value_template: "{{ 'Bestseller' in trigger.event.data.tags }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Neues HOLY Produkt!"
          message: "{{ trigger.event.data.title }} – {{ trigger.event.data.price }}€"
          data:
            image: "{{ trigger.event.data.image_url }}"
            url: "{{ trigger.event.data.url }}"
```

---

## 7. `manifest.json`

```json
{
  "domain": "holy_products",
  "name": "HOLY Products",
  "codeowners": [],
  "config_flow": true,
  "documentation": "https://github.com/...",
  "iot_class": "cloud_polling",
  "requirements": [],
  "version": "1.0.0"
}
```

- Keine externen Requirements nötig – `aiohttp` ist in HA enthalten.
- `iot_class: cloud_polling` da wir eine Cloud-API pollen.

---

## 8. Implementierungsreihenfolge

1. **`const.py`** – Konstanten definieren.
2. **`manifest.json`** – Metadaten anlegen.
3. **`coordinator.py`** – API-Abruf mit Paginierung, Erkennung neuer Produkte, Event-Firing.
4. **`config_flow.py`** – UI-Konfiguration mit Options Flow.
5. **`__init__.py`** – Integration Setup: Coordinator starten, Plattformen laden.
6. **`sensor.py`** – Sensoren registrieren.
7. **`strings.json` / `translations/de.json`** – UI-Texte.
8. **Tests** – Unit-Tests für Coordinator (Paginierung, neue Produkte), Config Flow, Sensoren.

---

## 9. Testen

### Unit-Tests

- **Coordinator**: Mock-API-Responses, Paginierung (1 Seite, mehrere Seiten), Erkennung neuer Produkte, Fehlerbehandlung.
- **Config Flow**: Validierung der Eingaben, Options Flow.
- **Sensoren**: Korrekte States und Attribute.

### Manueller Test

- Integration in einer HA-Dev-Instanz installieren.
- Prüfen: Sensoren erscheinen, Events werden gefeuert, Automatisierung funktioniert.

---

## 10. Offene Überlegungen

- **Rate Limiting**: Shopify kann Rate Limits haben. Bei HTTP 429 → exponentielles Backoff.
- **Persistenz**: Bekannte Produkt-IDs über `hass.data` oder `homeassistant.helpers.storage.Store` persistieren, damit nach HA-Neustart nicht alle Produkte als "neu" gelten.
- **Bilder-Proxy**: Optional Bilder über HA-Proxy bereitstellen für lokale Dashboards.
- **Varianten-Tracking**: Optional Events bei neuen Varianten bestehender Produkte.
