import json
import boto3
import logging
from decimal import Decimal, ROUND_HALF_UP

# Set up logging — visible in CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CloudComfortTable')

# ── Helpers ──────────────────────────────────────────────────────────────────

def to_decimal(value):
    """
    Convert float → Decimal for DynamoDB storage.
    boto3 refuses to store Python floats directly; this is the #1 cause of 500s.
    """
    return Decimal(str(value)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

def norm_temp(t):
    return max(0.0, min(1.0, 1.0 - abs(t - 22) / 13))

def norm_hum(h):
    return max(0.0, min(1.0, 1.0 - abs(h - 50) / 30))

def norm_co2(c):
    return 1.0 if c <= 800 else max(0.0, 1.0 - (c - 800) / 1200)

def norm_light(l):
    return max(0.0, min(1.0, 1.0 - abs(l - 400) / 400))

def norm_noise(n):
    return 1.0 if n <= 50 else max(0.0, 1.0 - (n - 50) / 40)

def compute_ci(data):
    ci = 100 * (
        0.30 * norm_temp(data['temperature']) +
        0.20 * norm_hum(data['humidity']) +
        0.25 * norm_co2(data['co2']) +
        0.15 * norm_light(data['light']) +
        0.10 * norm_noise(data['noise'])
    )
    return round(ci, 2)

def ci_label(ci):
    if ci >= 85:  return "Excellent"
    if ci >= 70:  return "Good"
    if ci >= 55:  return "Moderate"
    if ci >= 50:  return "Poor"
    return "Critical"

def make_response(status_code, body_dict):
    """Build an API Gateway–compatible response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",          # needed for dashboard
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": json.dumps(body_dict),
    }

# ── Handler ───────────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))

    # ── Handle CORS pre-flight ────────────────────────────────────────────────
    if event.get("httpMethod") == "OPTIONS":
        return make_response(200, {"message": "OK"})

    # ── Parse body ───────────────────────────────────────────────────────────
    try:
        raw_body = event.get("body") or "{}"
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError as e:
        logger.error("Bad JSON in request body: %s", e)
        return make_response(400, {"error": "Invalid JSON in request body"})

    # ── Validate required fields ──────────────────────────────────────────────
    required = ["room_id", "timestamp", "temperature", "humidity", "co2", "light", "noise"]
    missing = [f for f in required if f not in body]
    if missing:
        logger.error("Missing fields: %s", missing)
        return make_response(400, {"error": f"Missing required fields: {missing}"})

    # ── Compute CI ────────────────────────────────────────────────────────────
    try:
        ci = compute_ci(body)
        label = ci_label(ci)
        logger.info("Computed CI=%.2f (%s) for room %s", ci, label, body["room_id"])
    except Exception as e:
        logger.error("CI computation failed: %s", e)
        return make_response(500, {"error": "CI computation error", "detail": str(e)})

    # ── Write to DynamoDB ─────────────────────────────────────────────────────
    # IMPORTANT: All numeric floats must be converted to Decimal before storing.
    # Storing raw Python floats raises "Float types are not supported" and causes 500.
    try:
        item = {
            "room_id":     body["room_id"],
            "timestamp":   body["timestamp"],
            "temperature": to_decimal(body["temperature"]),
            "humidity":    to_decimal(body["humidity"]),
            "co2":         to_decimal(body["co2"]),
            "noise":       to_decimal(body["noise"]),
            "light":       to_decimal(body["light"]),
            "ci":          to_decimal(ci),
            "ci_label":    label,
        }
        table.put_item(Item=item)
        logger.info("Wrote item to DynamoDB for room=%s ts=%s", body["room_id"], body["timestamp"])
    except Exception as e:
        logger.error("DynamoDB write failed: %s", e)
        return make_response(500, {"error": "Database write failed", "detail": str(e)})

    return make_response(200, {"ci": ci, "ci_label": label, "room_id": body["room_id"]})