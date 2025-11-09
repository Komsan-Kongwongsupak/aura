from prefect import flow, task, get_run_logger
import pandas as pd
from sqlalchemy import create_engine
import boto3, os, io
from src.ingestion.validators import validate_dataframe_from_yaml

@task
def extract(filepath):
    df = pd.read_csv(filepath)
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
def load_to_postgres(df):
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
def ingest_pipeline():
    df = extract()
    df = validate(df)
    load_to_postgres(df)
    store_raw_in_minio(df)

if __name__ == "__main__":
    ingest_pipeline()
