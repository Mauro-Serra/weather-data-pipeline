import os
import psycopg2
import pandas as pd
import streamlit as st
import requests

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Weather Data Pipeline", layout="wide")

PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_DB = os.getenv("POSTGRES_DB", "pipeline")
PG_USER = os.getenv("POSTGRES_USER", "pipeline")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "pipeline")

DEFAULT_CITY = os.getenv("CITY_NAME", "Naples")

# -------------------- DB --------------------
@st.cache_resource
def get_conn():
    return psycopg2.connect(
        host=PG_HOST,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
    )

def load_data(conn, city: str, limit: int) -> pd.DataFrame:
    q = f"""
    SELECT ingestion_time, ts_utc, temperature_c, wind_speed, humidity, pressure
    FROM weather_observations
    WHERE city = %s
    ORDER BY ingestion_time DESC
    LIMIT {int(limit)};
    """
    return pd.read_sql(q, conn, params=(city,))

def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["ingestion_time"] = pd.to_datetime(df["ingestion_time"], utc=True, errors="coerce")
    df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True, errors="coerce")
    for col in ["temperature_c", "wind_speed", "humidity", "pressure"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def agg_last_per_ts(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["ts_utc", "ingestion_time"]).sort_values("ingestion_time")
    if d.empty:
        return d
    d = d.groupby("ts_utc", as_index=False).tail(1).sort_values("ts_utc")
    return d

# -------------------- DYNAMIC CITIES (Italy) --------------------
def geocode_city_it(city_name: str):
    """
    Geocoding via Nominatim (OpenStreetMap).
    Restringe la ricerca all'Italia.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{city_name}, Italy",
        "format": "json",
        "limit": 1,
    }
    headers = {"User-Agent": "weather-pipeline-dashboard/1.0"}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    if not data:
        return None
    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])
    return lat, lon

def add_city(conn, city: str, lat: float, lon: float, country_code="IT"):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO cities (city, lat, lon, country_code)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (city)
            DO UPDATE SET lat=EXCLUDED.lat, lon=EXCLUDED.lon, country_code=EXCLUDED.country_code;
            """,
            (city, lat, lon, country_code),
        )
    conn.commit()

def load_tracked_cities(conn):
    """
    Lista città tracciate (tabella cities). Se la tabella non esiste, torna [].
    """
    try:
        df = pd.read_sql("SELECT city FROM cities ORDER BY city;", conn)
        return df["city"].tolist()
    except Exception:
        return []

# -------------------- UI --------------------
st.title("🌦️ Weather Data Pipeline Dashboard")
conn = get_conn()

# Sidebar
with st.sidebar:
    st.header("Controls")

    # --- Add city section ---
    st.subheader("Add city (Italy)")
    new_city = st.text_input("Search city (e.g., Rome, Milan, Turin)", value="")

    add_clicked = st.button("Add / Update city")

    if add_clicked:
        if not new_city.strip():
            st.warning("Insert a city name.")
        else:
            try:
                res = geocode_city_it(new_city.strip())
                if res is None:
                    st.error("City not found in Italy.")
                else:
                    lat, lon = res
                    add_city(conn, new_city.strip(), lat, lon, "IT")
                    st.success(f"Added/updated: {new_city.strip()} (lat={lat:.4f}, lon={lon:.4f})")
                    st.rerun()
            except Exception as e:
                st.error(f"Geocoding failed: {e}")

    st.divider()

    # carica le città tracciate dal DB (tabella cities)
    cities = load_tracked_cities(conn)

    # fallback: se la tabella cities non esiste o è vuota
    if not cities:
        st.warning("No tracked cities found (table 'cities' missing or empty). Using DEFAULT_CITY fallback.")
        cities = [DEFAULT_CITY]

    # default selection
    default_index = cities.index(DEFAULT_CITY) if DEFAULT_CITY in cities else 0

    city = st.selectbox("City", cities, index=default_index)

    limit = st.slider(
        "Rows to load",
        min_value=200,
        max_value=5000,
        value=1500,
        step=100
    )

    view_mode = st.radio(
        "Chart X-axis",
        options=["ts_utc", "ingestion_time"],
        index=0
    )

    aggregation = st.checkbox(
        "Aggregate repeated ts_utc",
        value=True
    )

# -------------------- LOAD DATA --------------------
df_raw = load_data(conn, city, limit)
df_raw = coerce_types(df_raw)

if df_raw.empty:
    st.warning("No data yet for this city. If you just added it, ensure the producer is reading table 'cities'.")
    st.stop()

df_raw_sorted = df_raw.sort_values("ingestion_time")
latest = df_raw_sorted.iloc[-1]

# -------------------- KPI --------------------
k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Temp (°C)", "n/a" if pd.isna(latest["temperature_c"]) else f"{latest['temperature_c']:.1f}")
k2.metric("Wind", "n/a" if pd.isna(latest["wind_speed"]) else f"{latest['wind_speed']:.1f}")
k3.metric("Humidity", "n/a" if pd.isna(latest["humidity"]) else f"{latest['humidity']:.0f}")
k4.metric("Pressure", "n/a" if pd.isna(latest["pressure"]) else f"{latest['pressure']:.1f}")

last_ingest = latest["ingestion_time"]
now_utc = pd.Timestamp.now(tz="UTC")
lag_seconds = (now_utc - last_ingest).total_seconds() if pd.notna(last_ingest) else None
k5.metric("Pipeline lag (sec)", "n/a" if lag_seconds is None else f"{int(lag_seconds)}")

st.divider()

# -------------------- DATA FOR CHARTS --------------------
if aggregation:
    df_chart = agg_last_per_ts(df_raw)
else:
    df_chart = df_raw_sorted

xcol = "ts_utc" if view_mode == "ts_utc" else "ingestion_time"

temp_series = df_chart.set_index(xcol)[["temperature_c"]].dropna()
wind_series = df_chart.set_index(xcol)[["wind_speed"]].dropna()
pres_series = df_chart.set_index(xcol)[["pressure"]].dropna()
hum_series  = df_chart.set_index(xcol)[["humidity"]].dropna()

# -------------------- GRID 2x2 --------------------
st.subheader("📊 Weather Metrics")

c11, c12 = st.columns(2)
with c11:
    st.markdown("**Temperature**")
    st.line_chart(temp_series)

with c12:
    st.markdown("**Wind**")
    st.line_chart(wind_series)

c21, c22 = st.columns(2)
with c21:
    st.markdown("**Pressure**")
    st.line_chart(pres_series)

with c22:
    st.markdown("**Humidity**")
    st.line_chart(hum_series)

st.divider()

# -------------------- THROUGHPUT + DELTAS (side-by-side) --------------------
st.subheader("⚙️ Pipeline Monitoring")

tcol, dcol = st.columns(2)

with tcol:
    st.markdown("### Pipeline Throughput")
    df_counts = (
        df_raw.dropna(subset=["ts_utc"])
        .groupby("ts_utc")
        .size()
        .reset_index(name="count")
        .sort_values("ts_utc")
    )
    if df_counts.empty:
        st.info("Not enough data yet.")
    else:
        st.bar_chart(df_counts.set_index("ts_utc")[["count"]])

with dcol:
    st.markdown("### Deltas")

    df_delta_base = agg_last_per_ts(df_raw) if aggregation else df_raw_sorted
    df_delta_base = df_delta_base.dropna(subset=["ts_utc"]).sort_values("ts_utc")

    if len(df_delta_base) < 2:
        st.info("Not enough points yet to compute deltas.")
    else:
        df_delta_base["temp_delta"] = df_delta_base["temperature_c"].diff()
        df_delta_base["wind_delta"] = df_delta_base["wind_speed"].diff()
        df_delta_base["pressure_delta"] = df_delta_base["pressure"].diff()
        df_delta_base["humidity_delta"] = df_delta_base["humidity"].diff()

        last_row = df_delta_base.iloc[-1]

        m1, m2 = st.columns(2)
        m1.metric("Δ Temp", "n/a" if pd.isna(last_row["temp_delta"]) else f"{last_row['temp_delta']:+.2f} °C")
        m2.metric("Δ Wind", "n/a" if pd.isna(last_row["wind_delta"]) else f"{last_row['wind_delta']:+.2f}")

        m3, m4 = st.columns(2)
        m3.metric("Δ Pressure", "n/a" if pd.isna(last_row["pressure_delta"]) else f"{last_row['pressure_delta']:+.2f}")
        m4.metric("Δ Humidity", "n/a" if pd.isna(last_row["humidity_delta"]) else f"{last_row['humidity_delta']:+.2f}")

        st.caption("Deltas computed between the last two ts_utc points (after aggregation if enabled).")

st.divider()

# -------------------- RAW DATA --------------------
st.subheader("🗃️ Raw Data Table")

st.dataframe(
    df_raw.sort_values("ingestion_time", ascending=False).head(50),
    use_container_width=True
)