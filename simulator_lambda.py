"""
simulator_lambda.py — CloudComfort Simulator Lambda
Generates one batch of sensor readings for all 10 rooms and posts them to API Gateway.
Triggered by EventBridge every 5 minutes.

Deploy this as a separate Lambda function named: CloudComfortSimulator
"""

import json
import os
import random
import urllib.request
import urllib.error
import logging
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── Configuration ─────────────────────────────────────────────────────────────
# Set this as a Lambda environment variable: CLOUDCOMFORT_API_URL
API_ENDPOINT = os.environ.get("CLOUDCOMFORT_API_URL", "")

ROOMS = [
    "CR101", "CR102", "CR103", "CR104", "CR105",
    "CR106", "CR107", "CR108", "CR109", "CR110"
]

# ── Payload generation ────────────────────────────────────────────────────────

def generate_payload(room_id: str) -> dict:
    return {
        "room_id":     room_id,
        "temperature": round(random.uniform(20, 35), 2),
        "humidity":    round(random.uniform(30, 80), 2),
        "co2":         random.randint(400, 2000),
        "noise":       round(random.uniform(30, 90), 2),
        "light":       random.randint(100, 800),
        "timestamp":   datetime.now(timezone.utc).isoformat(),
    }

# ── HTTP sender (no requests library in Lambda by default) ───────────────────

def send_payload(payload: dict) -> bool:
    try:
        data = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(
            API_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            logger.info("✓ %s  CI=%.1f (%s)", payload["room_id"], body.get("ci", 0), body.get("ci_label", "?"))
            return True

    except urllib.error.HTTPError as e:
        logger.error("✗ %s  HTTP %d: %s", payload["room_id"], e.code, e.read().decode())
    except Exception as e:
        logger.error("✗ %s  Error: %s", payload["room_id"], e)
    return False

# ── Handler ───────────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    if not API_ENDPOINT:
        logger.error("CLOUDCOMFORT_API_URL environment variable not set")
        return {"statusCode": 500, "body": "API URL not configured"}

    logger.info("Simulating batch for %d rooms", len(ROOMS))
    results = {"success": 0, "failed": 0}

    for room in ROOMS:
        payload = generate_payload(room)
        if send_payload(payload):
            results["success"] += 1
        else:
            results["failed"] += 1

    logger.info("Batch complete — success: %d, failed: %d", results["success"], results["failed"])
    return {"statusCode": 200, "body": json.dumps(results)}