CREATE TABLE IF NOT EXISTS datasets (
  dataset_id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  source_url TEXT,
  s3_path TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS engines (
  engine_id SERIAL PRIMARY KEY,
  dataset_id INT NOT NULL REFERENCES datasets(dataset_id),
  data_type TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS engine_cycles (
  cycle_id BIGSERIAL PRIMARY KEY,
  engine_id INT NOT NULL REFERENCES engines(engine_id),
  cycle_number INT NOT NULL,
  ingested_at TIMESTAMPTZ DEFAULT now(),
  setting_1 FLOAT, setting_2 FLOAT, setting_3 FLOAT,
  sensor_1 FLOAT, sensor_2 FLOAT, sensor_3 FLOAT, sensor_4 FLOAT, sensor_5 FLOAT,
  sensor_6 FLOAT, sensor_7 FLOAT, sensor_8 FLOAT, sensor_9 FLOAT, sensor_10 FLOAT,
  sensor_11 FLOAT, sensor_12 FLOAT, sensor_13 FLOAT, sensor_14 FLOAT, sensor_15 FLOAT,
  sensor_16 FLOAT, sensor_17 FLOAT, sensor_18 FLOAT, sensor_19 FLOAT, sensor_20 FLOAT,
  sensor_21 FLOAT,
  rul INT,
  source_file TEXT
);

CREATE INDEX IF NOT EXISTS idx_engine_cycles_engine ON engine_cycles(engine_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_engine_cycle ON engine_cycles(engine_id, cycle_number);

CREATE TABLE IF NOT EXISTS ingestion_log (
  run_id SERIAL PRIMARY KEY,
  started_at TIMESTAMPTZ DEFAULT now(),
  finished_at TIMESTAMPTZ,
  source_file TEXT,
  records_processed INT,
  success BOOLEAN,
  error_message TEXT
);
