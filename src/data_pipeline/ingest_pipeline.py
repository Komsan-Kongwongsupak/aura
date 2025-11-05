from prefect import flow, task
import pandas as pd
from sqlalchemy import create_engine
import boto3, os, io

@task
def extract():
    df = pd.read_csv("data/raw/sensor_data.csv")
    return df

@task
def validate(df):
    assert "temperature" in df.columns
    return df

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
