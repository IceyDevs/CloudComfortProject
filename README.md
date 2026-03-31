# CloudComfort Analytics

A cloud-based smart classroom comfort monitoring system built on a serverless AWS architecture.

## Overview

CloudComfort Analytics simulates IoT sensor data — temperature, humidity, CO2, ambient light, and noise — and processes it in real time to compute an **Indoor Comfort Index (CI)** for each monitored classroom. Data is stored in Amazon DynamoDB and visualised through a live Streamlit dashboard, which also lets you start and stop the simulator with a single button.

## Architecture

```
Dashboard Button → Control Lambda → EventBridge Rule (every 5 min)
                                          ↓
                                   Simulator Lambda
                                          ↓
                              API Gateway → Lambda → DynamoDB → Dashboard
```

## Features

- Real-time comfort index computed from 5 environmental parameters
- Monitors 10 classrooms simultaneously (CR101–CR110)
- Live dashboard with auto-refresh, KPI cards, and sensor trend charts
- Automatic alerts when CI drops below 50 (Critical)
- Start/Stop simulator directly from the dashboard with a status indicator
- Fully serverless — no EC2 instances, no idle cost

## Comfort Index Formula

| Parameter   | Weight | Ideal Condition |
|-------------|--------|----------------|
| Temperature | 30%    | 20–24°C        |
| Humidity    | 20%    | 40–60%         |
| CO₂         | 25%    | < 800 ppm      |
| Light       | 15%    | 300–500 lux    |
| Noise       | 10%    | < 50 dB        |

**CI Classification:**
| Score    | Label     |
|----------|-----------|
| 85–100   | Excellent |
| 70–84    | Good      |
| 55–69    | Moderate  |
| 50–54    | Poor      |
| Below 50 | Critical  |

## Project Structure

| File | Description |
|------|-------------|
| `lambda_function.py` | AWS Lambda handler — receives sensor data, computes CI, writes to DynamoDB |
| `simulator_lambda.py` | AWS Lambda that generates sensor data — triggered by EventBridge every 5 minutes |
| `control_lambda.py` | AWS Lambda that enables/disables the EventBridge rule — called by the dashboard |
| `simulator.py` | Local IoT sensor simulator — for development and testing purposes |
| `dashboard.py` | Streamlit dashboard — live visualisation, alerts, and simulator control |
| `requirements.txt` | Python dependencies |

## AWS Services Used

| Service | Purpose |
|---------|---------|
| AWS Lambda | Serverless compute for data processing, simulation, and control |
| AWS API Gateway | HTTP entry point for sensor data ingestion |
| AWS DynamoDB | Real-time sensor data storage |
| AWS EventBridge | Scheduled trigger for the simulator Lambda (every 5 minutes) |

## Tech Stack

- **AWS Lambda** — serverless compute
- **AWS API Gateway** — HTTP entry point
- **AWS DynamoDB** — real-time data storage
- **AWS EventBridge** — scheduled simulator trigger
- **Python** — all Lambda functions and dashboard
- **Streamlit** — live dashboard UI

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure AWS credentials:
   ```bash
   aws configure
   ```

3. Start the local simulator (for development only):
   ```bash
   python simulator.py
   ```

4. Start the dashboard:
   ```bash
   streamlit run dashboard.py
   ```

## Deployment

- **Dashboard** — deployed on Streamlit Community Cloud, connected to this GitHub repo. AWS credentials are managed via Streamlit Secrets.
- **Lambdas** — deployed on AWS Lambda (Python 3.13 runtime).
- **Simulator** — runs as a cloud Lambda triggered by EventBridge, controlled via the dashboard Start/Stop button.
