# Weather Data Pipeline 🚀

A real-time data pipeline for ingesting, processing, and visualizing weather data from multiple cities in Italy.

The system collects weather observations via API, streams them through a message queue, stores them in a database, and provides an interactive analytics dashboard.

This project demonstrates a modern **data engineering architecture** including streaming ingestion, asynchronous processing, containerization, and data visualization.

---

# Architecture

The system follows a **producer → queue → consumer → database → dashboard** architecture.

```
           Open-Meteo API
                │
                ▼
        Producer (Python)
     Multi-city data ingestion
                │
                ▼
            RabbitMQ
        Message queue / buffer
                │
                ▼
        Consumer (Python)
     Data validation & storage
                │
                ▼
            PostgreSQL
       Persistent storage
                │
                ▼
        Streamlit Dashboard
     Real-time analytics UI
```

---

# Key Features

## Multi-City Data Ingestion

Cities can be dynamically added from the dashboard.

The system automatically:

1. Geocodes the city name
2. Stores coordinates in the database
3. Producer reads the updated city list
4. Weather data ingestion begins automatically

---

## Real-Time Data Pipeline

Weather data flows through the system in near real-time.

```
API → Producer → RabbitMQ → Consumer → PostgreSQL → Dashboard
```

This design ensures:

- decoupled components
- asynchronous processing
- scalable architecture

---

## Interactive Dashboard

The Streamlit dashboard provides:

### Weather Metrics

```
Temperature | Wind
------------|------
Pressure    | Humidity
```

### Pipeline Monitoring

```
Pipeline Throughput | Data Deltas
```

### Features

- dynamic city selection
- historical time-series visualization
- ingestion lag monitoring
- throughput metrics
- weather delta analysis
- raw data inspection

---

# Data Model

## weather_observations

Stores the collected weather observations.

| column | description |
|------|-------------|
| id | unique row identifier |
| city | city name |
| ts_utc | timestamp from weather API |
| temperature_c | temperature in Celsius |
| wind_speed | wind speed |
| humidity | relative humidity |
| pressure | atmospheric pressure |
| ingestion_time | pipeline ingestion timestamp |

---

## cities

List of tracked cities.

| column | description |
|------|-------------|
| city | city name |
| lat | latitude |
| lon | longitude |
| country_code | country identifier |
| created_at | timestamp when city was added |

---

# Technologies Used

### Data Engineering

- Python
- RabbitMQ
- PostgreSQL
- Docker

### Data Processing

- Pandas
- psycopg2

### Visualization

- Streamlit

### APIs

- Open-Meteo Weather API
- OpenStreetMap Nominatim Geocoding

---

# Project Structure

```
data-pipeline
│
├── docker-compose.yml
│
├── services
│   │
│   ├── producer
│   │   ├── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── consumer
│   │   ├── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── dashboard
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── db
│       └── init.sql
│
└── README.md
```

---

# Running the Project

## 1 Clone the repository

```bash
git clone https://github.com/yourusername/weather-data-pipeline.git
cd weather-data-pipeline
```

---

## 2 Start the pipeline

```bash
docker compose up --build
```

This will start:

- PostgreSQL
- RabbitMQ
- Producer
- Consumer
- Streamlit Dashboard

---

## 3 Open the dashboard

```
http://localhost:8501
```

---

# Adding New Cities

Cities can be added directly from the dashboard.

Example:

```
Search city: Rome
Add / Update city
```

The system will:

1. Geocode the city using OpenStreetMap
2. Store coordinates in the database
3. Producer will automatically start ingesting data

---

# Example Workflow

```
Add city (Rome)
        │
        ▼
Geocoding via Nominatim
        │
        ▼
INSERT INTO cities
        │
        ▼
Producer reads city list
        │
        ▼
Weather API request
        │
        ▼
RabbitMQ queue
        │
        ▼
Consumer processes message
        │
        ▼
PostgreSQL storage
        │
        ▼
Dashboard visualization
```

---

# Example Queries

Retrieve latest observations:

```sql
SELECT *
FROM weather_observations
ORDER BY ingestion_time DESC
LIMIT 10;
```

Retrieve weather history for a city:

```sql
SELECT *
FROM weather_observations
WHERE city = 'Rome'
ORDER BY ts_utc;
```

---

# Monitoring

The dashboard includes pipeline monitoring features.

### Pipeline Lag

Measures delay between ingestion and current time.

### Throughput

Shows number of messages processed per API timestamp.

### Weather Deltas

Shows change between the latest two weather measurements.

---

# Possible Improvements

Future extensions for the project:

- Kafka streaming pipeline
- Airflow orchestration
- Grafana monitoring
- multi-city comparison charts
- anomaly detection for weather patterns
- cloud deployment (AWS / GCP)

---

# Learning Objectives

This project demonstrates practical skills in:

- data pipeline design
- message queues
- asynchronous processing
- containerized microservices
- real-time analytics dashboards

---

# License

MIT License