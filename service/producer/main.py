import json
import os
import time
from datetime import datetime, timezone

import pika
import psycopg2
import requests

# ---------- ENV ----------
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
QUEUE = os.getenv("RABBITMQ_QUEUE", "weather.raw")

PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_DB = os.getenv("POSTGRES_DB", "pipeline")
PG_USER = os.getenv("POSTGRES_USER", "pipeline")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "pipeline")

POLL_SECONDS = int(os.getenv("POLL_SECONDS", "60"))
# ogni quanto rileggo l'elenco città dal DB (in secondi)
CITIES_REFRESH_SECONDS = int(os.getenv("CITIES_REFRESH_SECONDS", "60"))

API_URL = "https://api.open-meteo.com/v1/forecast"


# ---------- Connections ----------
def connect_db():
    return psycopg2.connect(
        host=PG_HOST,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
    )

def connect_rabbit():
    params = pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=60)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.queue_declare(queue=QUEUE, durable=True)
    return conn, ch


# ---------- DB queries ----------
def load_cities_from_db(db_conn):
    """
    Legge le città tracciate dalla tabella cities.
    Ritorna lista di dict: {city, lat, lon, country_code}
    """
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT city, lat, lon, COALESCE(country_code, 'IT')
            FROM cities
            ORDER BY city;
        """)
        rows = cur.fetchall()

    cities = []
    for city, lat, lon, cc in rows:
        cities.append({"city": city, "lat": float(lat), "lon": float(lon), "country_code": cc})
    return cities


# ---------- Weather fetch ----------
def fetch_weather(lat: float, lon: float):
    """
    Fetch current weather from Open-Meteo.
    Ritorna dict con ts_utc, temperature, wind, pressure + humidity (best effort).
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m,pressure_msl",
        "hourly": "relative_humidity_2m",
        "timezone": "UTC",
    }

    r = requests.get(API_URL, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    current = data.get("current", {})
    ts = current.get("time")  # ISO string (UTC)

    # humidity: prendo primo valore hourly (approssimazione)
    humidity = None
    hourly = data.get("hourly", {})
    if isinstance(hourly, dict) and "relative_humidity_2m" in hourly:
        arr = hourly.get("relative_humidity_2m")
        if isinstance(arr, list) and len(arr) > 0:
            humidity = arr[0]

    return {
        "ts_utc": ts,
        "temperature_c": current.get("temperature_2m"),
        "wind_speed": current.get("wind_speed_10m"),
        "pressure": current.get("pressure_msl"),
        "humidity": humidity,
    }


# ---------- Main ----------
def main():
    # Wait for Postgres
    while True:
        try:
            db = connect_db()
            db.autocommit = True
            break
        except Exception as e:
            print(f"[producer] Postgres not ready yet: {e}")
            time.sleep(3)

    # Wait for RabbitMQ
    while True:
        try:
            rmq_conn, ch = connect_rabbit()
            break
        except Exception as e:
            print(f"[producer] RabbitMQ not ready yet: {e}")
            time.sleep(3)

    print("[producer] started (multi-city)")

    cities_cache = []
    last_cities_refresh = 0.0

    while True:
        try:
            # refresh cities list
            now = time.time()
            if (now - last_cities_refresh) >= CITIES_REFRESH_SECONDS or not cities_cache:
                cities_cache = load_cities_from_db(db)
                last_cities_refresh = now
                print(f"[producer] loaded {len(cities_cache)} tracked cities")

            if not cities_cache:
                print("[producer] no cities in DB. Add one from dashboard.")
                time.sleep(POLL_SECONDS)
                continue

            # fetch & publish for each city
            for c in cities_cache:
                try:
                    w = fetch_weather(c["lat"], c["lon"])

                    msg = {
                        "source": "open-meteo",
                        "city": c["city"],
                        "country_code": c["country_code"],
                        "lat": c["lat"],
                        "lon": c["lon"],
                        "ts_utc": w["ts_utc"],
                        "temperature_c": w["temperature_c"],
                        "wind_speed": w["wind_speed"],
                        "pressure": w["pressure"],
                        "humidity": w["humidity"],
                        "produced_at_utc": datetime.now(timezone.utc).isoformat(),
                    }

                    body = json.dumps(msg).encode("utf-8")
                    ch.basic_publish(
                        exchange="",
                        routing_key=QUEUE,
                        body=body,
                        properties=pika.BasicProperties(delivery_mode=2),  # persistent
                    )

                    print(f"[producer] published: {msg['city']} ts={msg['ts_utc']} temp={msg['temperature_c']}")

                    # Piccola pausa per non martellare l'API se hai molte città
                    time.sleep(0.2)

                except Exception as e:
                    print(f"[producer] city fetch/publish failed for {c.get('city')}: {e}")

        except Exception as e:
            print(f"[producer] loop error: {e}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()