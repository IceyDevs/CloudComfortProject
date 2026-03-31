import json
import os
import random
import time
import logging
from datetime import datetime, timezone

import requests

# ── Configuration ─────────────────────────────────────────────────────────────


API_ENDPOINT = "https://hvq352wih4.execute-api.eu-north-1.amazonaws.com/ingest"


ROOMS          = ["CR101", "CR102", "CR103", "CR104", "CR105", "CR106", "CR107", "CR108", "CR109", "CR110"]   # rooms to simulate
INTERVAL_SECS  = 5                             # seconds between batches
REQUEST_TIMEOUT = 10                           # seconds before giving up
MAX_RETRIES    = 3                             # retries on transient failure

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Payload generation ────────────────────────────────────────────────────────

def generate_payload(room_id: str) -> dict:
    """Return a realistic-ish sensor reading for the given room."""
    return {
        "room_id":     room_id,
        "temperature": round(random.uniform(20, 35), 2),    # °C
        "humidity":    round(random.uniform(30, 80), 2),    # %
        "co2":         random.randint(400, 2000),           # ppm
        "noise":       round(random.uniform(30, 90), 2),    # dB(A)
        "light":       random.randint(100, 800),            # lux
        "timestamp":   datetime.now(timezone.utc).isoformat(),
    }

# ── HTTP sender ───────────────────────────────────────────────────────────────

def send_payload(payload: dict) -> bool:
    """
    POST payload to API Gateway. Returns True on success.
    Retries up to MAX_RETRIES times on 5xx or network errors.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                API_ENDPOINT,
                json=payload,
                timeout=REQUEST_TIMEOUT,
                headers={"Content-Type": "application/json"},
            )

            if resp.status_code == 200:
                data = resp.json()
                log.info(
                    "✓ %s  CI=%.1f (%s)",
                    payload["room_id"],
                    data.get("ci", 0),
                    data.get("ci_label", "?"),
                )
                return True

            # Client error (4xx) — no point retrying
            if 400 <= resp.status_code < 500:
                log.error(
                    "✗ %s  HTTP %d (client error, no retry): %s",
                    payload["room_id"], resp.status_code, resp.text[:200],
                )
                return False

            # Server error (5xx) — retry
            log.warning(
                "✗ %s  HTTP %d (attempt %d/%d): %s",
                payload["room_id"], resp.status_code, attempt, MAX_RETRIES, resp.text[:200],
            )

        except requests.exceptions.Timeout:
            log.warning("✗ %s  Timeout (attempt %d/%d)", payload["room_id"], attempt, MAX_RETRIES)
        except requests.exceptions.ConnectionError as e:
            log.warning("✗ %s  Connection error (attempt %d/%d): %s", payload["room_id"], attempt, MAX_RETRIES, e)
        except Exception as e:
            log.error("✗ %s  Unexpected error: %s", payload["room_id"], e)
            return False

        if attempt < MAX_RETRIES:
            time.sleep(2 ** attempt)   # exponential back-off: 2s, 4s

    return False

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    log.info("CloudComfort simulator starting — rooms: %s — interval: %ds", ROOMS, INTERVAL_SECS)

    while True:
        for room in ROOMS:
            payload = generate_payload(room)
            log.debug("Sending: %s", json.dumps(payload))
            send_payload(payload)

        time.sleep(INTERVAL_SECS)

if __name__ == "__main__":
    main()