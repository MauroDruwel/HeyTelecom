# HeyTelecom Docker

Flask REST API for HeyTelecom.

## Quick Start

```bash
docker run -d \
  -p 8099:8099 \
  -e HEYTELECOM_EMAIL="your@email.com" \
  -e HEYTELECOM_PASSWORD="your_password" \
  -v heytelecom-data:/data \
  ghcr.io/maurodruwel/heytelecom:latest
```

Or with docker-compose:

```bash
docker-compose up -d
```

## Environment Variables

- `HEYTELECOM_EMAIL` - Your Hey Telecom email (required)
- `HEYTELECOM_PASSWORD` - Your Hey Telecom password (required)
- `PORT` - API port (default: 8099)
- `USER_DATA_DIR` - Browser data directory (default: /data/hey_browser_data)

## API Endpoints

- `GET /` - API information
- `GET /account` - Complete account data
- `GET /products` - All products
- `GET /invoice` - Latest invoice
- `POST /login` - Force fresh login

## Example

```bash
curl http://localhost:8099/account
```

## Home Assistant

```yaml
sensor:
  - platform: rest
    name: Hey Telecom Data Usage
    resource: http://localhost:8099/products
    scan_interval: 1800
    value_template: >
      {% if value_json.products and value_json.products|length > 0 %}
        {{ value_json.products[0].usage.data.used | default(0) }}
      {% else %}
        0
      {% endif %}
    unit_of_measurement: "GB"
```
