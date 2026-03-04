DROP TABLE IF EXISTS weather_observations;

CREATE TABLE weather_observations (
  id BIGSERIAL PRIMARY KEY,
  city TEXT NOT NULL,
  ts_utc TIMESTAMPTZ NOT NULL,
  temperature_c DOUBLE PRECISION,
  wind_speed DOUBLE PRECISION,
  humidity DOUBLE PRECISION,
  pressure DOUBLE PRECISION,
  ingestion_time TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cities (
  city TEXT PRIMARY KEY,
  lat DOUBLE PRECISION NOT NULL,
  lon DOUBLE PRECISION NOT NULL,
  country_code TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO cities (city, lat, lon, country_code)
VALUES ('Naples', 40.8518, 14.2681, 'IT')
ON CONFLICT (city) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_weather_city_ingestion
ON weather_observations(city, ingestion_time DESC);

CREATE INDEX idx_weather_city_ts
ON weather_observations(city, ts_utc);

CREATE INDEX idx_weather_ingestion
ON weather_observations(ingestion_time);

CREATE INDEX idx_weather_city_ingestion
ON weather_observations(city, ingestion_time DESC);
