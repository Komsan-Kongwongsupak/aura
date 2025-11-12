from prefect import flow, task, get_run_logger
import numpy as np
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
import boto3, os, io, sys, json
from src.ingestion.validators import validate_dataframe_from_yaml

col_engid = "engine_id"
col_cycno = "cycle_number"
cols_setting = [f"setting_{i}" for i in range(1, 4)]
cols_sensor = [f"sensor_{i}" for i in range(1, 22)]

@task
def extract(filepath, data_type, rul_path=None):
    cols_placeholder = ["empty_1", "empty_2"]
    columns = [col_engid, col_cycno] + cols_setting + cols_sensor + cols_placeholder

    df = pd.read_table(filepath, sep=" ", header=None, names=columns).drop(cols_placeholder, axis=1)
    src_file = {"data": filepath}

    if data_type == "train":
        df = pd.merge(df, df.groupby("engine_id").agg(last_cycle_number=("cycle_number", "max")), on="engine_id", how="left")
        df["rul"] = df["last_cycle_number"] - df["cycle_number"]
        df = df.drop("last_cycle_number", axis=1)

    elif data_type == "test":
        if rul_path is not None:
            df_rul = pd.read_table(rul_path, header=None, names=["rul_last"])
            df_rul["engine_id"] = df_rul.index + 1
            df = pd.merge(df, df_rul, on="engine_id", how="left")
            df = pd.merge(df, df.groupby("engine_id").agg(last_cycle_number=("cycle_number", "max")), on="engine_id", how="left")
            df["rul"] = df["rul_last"] + (df["last_cycle_number"] - df["cycle_number"])
            df = df.drop(["rul_last", "last_cycle_number"], axis=1)

        else:
            df["rul"] = np.nan
        
        src_file["rul"] = rul_path

    df["source_file"] = json.dumps(src_file)
    return df

@task
def validate(df):
    if "engine_id" not in df.columns:
        raise ValueError(f"Missing required columns: engine_id")
    
    df["ingested_at"] = pd.to_datetime(datetime.now(), errors="coerce")

    if df["ingested_at"].isna().any():
        raise ValueError("Some ingested_at values could not be parsed")
    
    sensor_cols = [c for c in df.columns if c.startswith("sensor_")]
    df[sensor_cols] = df[sensor_cols].apply(pd.to_numeric, errors="coerce")
    return df

@task
def load_to_postgres(df, dataset_id):
    engine = create_engine(os.getenv("POSTGRES_URL"))
    df.to_sql("telemetry", engine, if_exists="append", index=False)

@task
def store_raw_in_minio(df):
    s3 = boto3.client(
        "s3",
        endpoint_url=os.getenv("MINIO_ENDPOINT"),
        aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
        aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD"),
    )
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=os.getenv("S3_BUCKET"), Key="raw/sensor_data.csv", Body=csv_buffer.getvalue())

@flow
def ingest_pipeline(name, source_url, data_type, rul_path=None):
    df = extract(source_url, data_type, rul_path)
    df = validate(df)
    load_to_postgres(df)
    store_raw_in_minio(df)

if __name__ == "__main__":
    args = sys.argv[1:]
    ingest_pipeline(*args)
