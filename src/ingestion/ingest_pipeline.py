from prefect import flow, task, get_run_logger
import pandas as pd
from sqlalchemy import create_engine
import boto3, os, io, sys
from src.ingestion.validators import validate_dataframe_from_yaml

@task
def extract(filepath, data_type):
    col_engid = "engine_id"
    col_cycno = "cycle_number"
    cols_setting = [f"setting_{i}" for i in range(1, 4)]
    cols_sensor = [f"sensor_{i}" for i in range(1, 22)]
    cols_placeholder = ["empty_1", "empty_2"]
    columns = [col_engid, col_cycno] + cols_setting + cols_sensor + cols_placeholder
    
    df = pd.read_table(filepath, sep=" ", header=None, names=columns).drop(cols_placeholder, axis=1)
    return df

@task
def validate(df):
    logger = get_run_logger()
    try:
        # try to coerce / validate
        validated = validate_dataframe_from_yaml(df, SCHEMA_PATH)
        logger.info(f"Validation passed: {len(validated)} rows.")
        return validated
    except Exception as e:
        # Pandera raises SchemaError with a detailed report; log and re-raise
        logger.error("Validation failed: %s", e)
        # Optionally: save the failing dataframe sample for debugging
        df.head(50).to_csv("data/failed_sample.csv", index=False)
        raise

@task
def compute_rul_train(df):
    df = pd.merge(df, df.groupby("engine_id").agg(last_cycle_number=("cycle_number", "max")), on="engine_id", how="left")
    df["rul"] = df["last_cycle_number"] - df["cycle_number"]
    return df.drop("last_cycle_number", axis=1)

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
def ingest_pipeline(name, source_url, data_type):
    df = extract(source_url, data_type)
    df = validate(df)
    load_to_postgres(df)
    store_raw_in_minio(df)

if __name__ == "__main__":
    ingest_pipeline(sys.argv[1], sys.argv[2], sys.argv[3])
