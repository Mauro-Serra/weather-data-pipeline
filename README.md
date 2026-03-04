# 🌦 Weather Data Pipeline

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-Message%20Queue-orange)
![License](https://img.shields.io/badge/License-MIT-green)

A **real-time data engineering pipeline** that ingests, processes, and visualizes weather data from multiple cities.

The system collects weather observations from an external API, streams them through a message queue, stores them in a relational database, and exposes the data through an interactive analytics dashboard.

This project demonstrates a modern **event-driven data pipeline architecture** using containerized microservices.

---

# 🚀 Features

- Real-time weather data ingestion
- Event-driven architecture using message queues
- Multi-city tracking with dynamic city registration
- Interactive analytics dashboard
- Pipeline monitoring metrics
- Containerized infrastructure with Docker

---

# 🏗 Architecture

The system follows a **streaming data pipeline architecture**.

```
         Weather API
             │
             ▼
      Producer Service
   (data ingestion layer)
             │
             ▼
          RabbitMQ
      (message broker)
             │
             ▼
      Consumer Service
     (data processing)
             │
             ▼
         PostgreSQL
       (data storage)
             │
             ▼
     Streamlit Dashboard
     (data visualization)
```

### Pipeline Flow

```
API → Producer → RabbitMQ → Consumer → PostgreSQL → Dashboard
```

This architecture enables:

- decoupled services
- asynchronous processing
- scalable ingestion
- fault-tolerant message handling

---

# 📊 Dashboard

The Streamlit dashboard provides **real-time monitoring and analytics**.

### Weather Metrics

```
Temperature | Wind
------------|------
Pressure    | Humidity
```

### Pipeline Monitoring

```
Throughput | Data Deltas
```

### Dashboard Capabilities

- dynamic city selection
- historical time-series charts
- ingestion delay monitoring
- message throughput visualization
- weather change (delta) analysis
- raw data inspection

---

# 🗂 Data Model

## weather_observations

Stores weather measurements collected from the API.

| column | description |
|------|-------------|
| id | unique identifier |
| city | city name |
| ts_utc | API timestamp |
| temperature_c | temperature in Celsius |
| wind_speed | wind speed |
| humidity | relative humidity |
| pressure | atmospheric pressure |
| ingestion_time | ingestion timestamp |

---

## cities

Stores the list of tracked cities.

| column | description |
|------|-------------|
| city | city name |
| lat | latitude |
| lon | longitude |
| country_code | country identifier |
| created_at | timestamp when the city was added |

---

# ⚙ Tech Stack

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

### External APIs

- Open-Meteo Weather API
- OpenStreetMap Nominatim Geocoding

---

# 📂 Project Structure

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

# ▶ Running the Project

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

This launches the entire infrastructure:

- PostgreSQL database
- RabbitMQ message broker
- Producer service
- Consumer service
- Streamlit analytics dashboard

---

## 3 Open the dashboard

```
http://localhost:8501
```

---

# 🌍 Adding New Cities

Cities can be dynamically added from the dashboard.

Example:

```
Search city: Rome
Add / Update city
```

The system will:

1. Geocode the city using OpenStreetMap
2. Store coordinates in the database
3. Producer automatically starts collecting weather data

---

# 🔍 Example Queries

Retrieve latest observations:

```sql
SELECT *
FROM weather_observations
ORDER BY ingestion_time DESC
LIMIT 10;
```

Retrieve historical data for a city:

```sql
SELECT *
FROM weather_observations
WHERE city = 'Rome'
ORDER BY ts_utc;
```

---

# 📈 Monitoring

The dashboard includes built-in pipeline monitoring.

### Pipeline Lag

Measures delay between ingestion time and current time.

### Throughput

Displays number of processed messages per API timestamp.

### Weather Deltas

Shows variation between the latest weather measurements.

---

# 🔮 Future Improvements

Possible extensions:

- Kafka streaming pipeline
- Airflow orchestration
- Grafana monitoring
- multi-city comparison analytics
- anomaly detection
- cloud deployment (AWS / GCP)

---

# 🎓 Learning Objectives

This project demonstrates skills in:

- event-driven data pipelines
- streaming ingestion
- message queue architectures
- containerized microservices
- real-time data analytics

---

# 📄 License

MIT License