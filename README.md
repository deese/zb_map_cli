# zb_map — Zigbee Network Map Tool

CLI tool that queries a Zigbee2MQTT broker via MQTT and dumps the full network topology — node names, link pairs, and LQI values — to a timestamped text report and a raw JSON backup.

## Requirements

- Python 3.8+
- `paho-mqtt`

```bash
pip install paho-mqtt
```

## Configuration

Copy `.env.example` to `.env` and fill in your broker details:

```
MQTT_BROKER=192.168.1.100
MQTT_PORT=1883
MQTT_USER=your_user
MQTT_PASSWORD=your_password
BASE_TOPIC=zigbee2mqtt
```

All variables are optional and fall back to `127.0.0.1:1883` with no auth and the `zigbee2mqtt` base topic.

## Usage

**Live query** — connects to the broker, requests a fresh network map, and saves the output:

```bash
python zb_map.py
```

**Offline parse** — re-parses an existing raw JSON dump without hitting MQTT:

```bash
python zb_map.py --file zigbee_network_raw_<timestamp>.json
```

## Output

Each run produces two timestamped files:

| File | Contents |
|---|---|
| `zigbee_network_raw_<ts>.json` | Full unmodified payload from the broker |
| `zigbee_network_parsed_<ts>.txt` | Human-readable topology table with LQI values |

Links with LQI < 50 are flagged as `(LOW LQI)` in both the file and console output.

## Example output

```
Source                         -> Target                         | LQI
---------------------------------------------------------------------------
coordinator                    -> living_room_bulb               | 254
living_room_bulb               -> kitchen_plug                   | 87
kitchen_plug                   -> bedroom_sensor                  | 43   (LOW LQI)
```
