import json
import os
import time
from datetime import datetime, timezone

import pika
import psycopg2
from pydantic import BaseModel, ValidationError


# ---------- ENV ----------
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
QUEUE = os.getenv("RABBITMQ_QUEUE", "weather.raw")

PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_DB = os.getenv("POSTGRES_DB", "pipeline")
PG_USER = os.getenv("POSTGRES_USER", "pipeline")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "pipeline")


# ---------- MODELS ----------
class WeatherMsg(BaseModel):
    source: str
    city: str
    ts_utc: str
    temperature_c: float | None = None
    wind_speed: float | None = None
    humidity: float | None = None
    pressure: float | None = None


# ---------- DB ----------
INSERT_SQL = """
INSERT INTO weather_observations (
  city, ts_utc, temperature_c, wind_speed, humidity, pressure, ingestion_time
)
VALUES (%s, %s, %s, %s, %s, %s, %s);
"""


def connect_db():
    return psycopg2.connect(
        host=PG_HOST,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
    )


# ---------- RABBIT ----------
def connect_rabbit():
    params = pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=60)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.queue_declare(queue=QUEUE, durable=True)
    ch.basic_qos(prefetch_count=20)
    return conn, ch


def parse_ts(ts_str: str) -> datetime:
    # open-meteo può dare "2026-03-04T08:45" o "...Z"
    s = ts_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def main():
    # Wait Postgres
    while True:
        try:
            db = connect_db()
            db.autocommit = True
            break
        except Exception as e:
            print(f"[consumer] Postgres not ready yet: {e}")
            time.sleep(3)

    # Wait RabbitMQ
    while True:
        try:
            rmq_conn, ch = connect_rabbit()
            break
        except Exception as e:
            print(f"[consumer] RabbitMQ not ready yet: {e}")
            time.sleep(3)

    cur = db.cursor()
    print("[consumer] started (INSERT mode)")

    def callback(channel, method, properties, body: bytes):
        try:
            payload = json.loads(body.decode("utf-8"))
            msg = WeatherMsg(**payload)

            ts = parse_ts(msg.ts_utc)
            ingestion_time = datetime.now(timezone.utc)

            cur.execute(
                INSERT_SQL,
                (
                    msg.city,
                    ts,
                    msg.temperature_c,
                    msg.wind_speed,
                    msg.humidity,
                    msg.pressure,
                    ingestion_time,
                ),
            )

            channel.basic_ack(delivery_tag=method.delivery_tag)
            print(f"[consumer] stored row: {msg.city} ts={msg.ts_utc} ingested={ingestion_time.isoformat()}")

        except (json.JSONDecodeError, ValidationError) as e:
            print(f"[consumer] bad message (discarded): {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except Exception as e:
            # Qui requeue=True può creare loop infiniti se l'errore è permanente.
            print(f"[consumer] processing error (discarded): {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    ch.basic_consume(queue=QUEUE, on_message_callback=callback)
    ch.start_consuming()


if __name__ == "__main__":
    main()