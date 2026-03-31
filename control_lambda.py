"""
control_lambda.py — CloudComfort Simulator Control
Enables or disables the EventBridge rule that triggers the simulator.
Called directly by the Streamlit dashboard.

Deploy this as a separate Lambda function named: CloudComfortSimulatorControl

Required IAM permissions for this Lambda's role:
  - events:EnableRule
  - events:DisableRule
  - events:DescribeRule
"""

import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

events = boto3.client("events")

# Name of the EventBridge rule that triggers CloudComfortSimulator
RULE_NAME = "CloudComfortSimulatorRule"

def make_response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": json.dumps(body_dict),
    }

def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))

    # Handle CORS pre-flight
    if event.get("httpMethod") == "OPTIONS":
        return make_response(200, {"message": "OK"})

    # Parse action from body
    try:
        body   = json.loads(event.get("body") or "{}")
        action = body.get("action", "").lower()   # "start" or "stop" or "status"
    except Exception as e:
        return make_response(400, {"error": f"Invalid request body: {e}"})

    try:
        if action == "start":
            events.enable_rule(Name=RULE_NAME)
            logger.info("EventBridge rule enabled: %s", RULE_NAME)
            return make_response(200, {"status": "running", "message": "Simulator started"})

        elif action == "stop":
            events.disable_rule(Name=RULE_NAME)
            logger.info("EventBridge rule disabled: %s", RULE_NAME)
            return make_response(200, {"status": "stopped", "message": "Simulator stopped"})

        elif action == "status":
            rule = events.describe_rule(Name=RULE_NAME)
            status = "running" if rule["State"] == "ENABLED" else "stopped"
            return make_response(200, {"status": status})

        else:
            return make_response(400, {"error": f"Unknown action '{action}'. Use 'start', 'stop', or 'status'."})

    except events.exceptions.ResourceNotFoundException:
        return make_response(404, {"error": f"EventBridge rule '{RULE_NAME}' not found. Please create it first."})
    except Exception as e:
        logger.error("Control action failed: %s", e)
        return make_response(500, {"error": str(e)})