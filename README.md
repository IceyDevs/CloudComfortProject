# CloudComfort Analytics

A cloud-based smart classroom comfort monitoring system built on a serverless AWS architecture.

## Overview

CloudComfort Analytics simulates IoT sensor data — temperature, humidity, CO2, ambient light, and noise — and processes it in real time to compute an **Indoor Comfort Index (CI)** for each monitored classroom. Data is stored in Amazon DynamoDB and visualised through a live Streamlit dashboard.

## Architecture
```
IoT Simulator → API Gateway → AWS Lambda → DynamoDB → Streamlit Dashboard
```

## Features

- Real-time comfort index computed from 5 environmental parameters
- Monitors 10 classrooms simultaneously (CR101–CR110)
- Live dashboard with auto-refresh, KPI cards, and sensor trend charts
- Automatic alerts when CI drops below 50 (Critical)
- Fully serverless — no EC2 instances, no idle cost

## Comfort Index Formula

| Parameter | Weight | Ideal Condition |
|-----------|--------|----------------|
| Temperature | 30% | 20–24°C |
| Humidity | 20% | 40–60% |
| CO₂ | 25% | < 800 ppm |
| Light | 15% | 300–500 lux |
| Noise | 10% | < 50 dB |

## Project Structure

| File | Description |
|------|-------------|
| `lambda_function.py` | AWS Lambda handler — computes CI and writes to DynamoDB |
| `simulator.py` | IoT sensor data simulator — sends readings to API Gateway |
| `dashboard.py` | Streamlit dashboard — live visualisation of comfort data |
| `requirements.txt` | Python dependencies |

## Tech Stack

- **AWS Lambda** — serverless compute
- **AWS API Gateway** — HTTP entry point
- **AWS DynamoDB** — real-time data storage
- **Python** — Lambda, simulator, and dashboard
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

3. Start the simulator:
```bash
   python simulator.py
```

4. Start the dashboard:
```bash
   streamlit run dashboard.py
```

## Deployment

Dashboard is deployed on Streamlit Community Cloud. AWS credentials are managed via Streamlit Secrets.