# System Architecture — AURA (Autonomous Understanding and Reliability Analytics)

> **Purpose:** This document describes the end-to-end architecture for the AURA predictive-maintenance ML platform. It is the single source of truth for Phase 1 design decisions, component responsibilities, data formats, and an implementation roadmap.

---

## Table of Contents

1. Overview
2. High-level Architecture Diagram (Mermaid)
3. Component Descriptions
4. Data Storage & Formats
5. Data Flow (End-to-end)
6. Security, Governance & SSHE considerations
7. Observability, Monitoring & Retraining
8. Implementation Phases & Roadmap
9. Deliverables for Phase 1
10. Project File Structure & Example Configs
11. Decisions & Tradeoffs
12. Next Steps

---

## 1. Overview

AURA is an ML platform to predict equipment failures and enable proactive maintenance for ARV-like industrial applications (air, land, sea). It demonstrates the design and implementation of a production-oriented ML system that handles structured and unstructured data, automated pipelines, model lifecycle management, deployment, monitoring, and governance.

**Primary goals**

* Ingest and store sensor and operational data (structured & unstructured)
* Build repeatable ML pipelines (ETL → Feature Engineering → Train → Evaluate)
* Deploy model(s) as containerized services
* Monitor model performance and automate retraining
* Document governance, safety, and compliance considerations

**Success metrics (example)**

* Model: recall, precision, F1 for failure detection; target thresholds defined per dataset
* System: reproducible end-to-end run, containerized deployment
* Process: retraining and redeployment triggered automatically when drift detected

---

## 2. High-level Architecture Diagram (Mermaid)

```mermaid
flowchart TD
  subgraph Sources
    A[IoT / Sensor Streams / External APIs]
  end

  A --> B[Data Ingestion Pipeline (Prefect)]
  B --> C1[S3 / MinIO (raw & artifacts)]
  B --> C2[PostgreSQL (processed / feature tables)]

  C1 --> D[ML Pipeline<br/>(ETL → Feature Eng → Train → Eval)]
  C2 --> D
  D --> E[Feature Store (Feast) / Serving Tables]
  D --> F[Model Registry / Artifacts (MLflow / S3)]
  F --> G[FastAPI Model Deployment<br/>(Docker / Container)]
  G --> H[Consumers / Business Apps / Dashboards]

  subgraph Ops
    I[Monitoring & Retraining (Prefect + MLflow)]
    J[Observability (Prometheus + Grafana)]
    K[Alerting (Slack / Email)]
    L[Security & Governance<br/>(Secrets, IAM, Audit)]
    M[Schema Registry / Data Catalog]
  end

  H --> I
  G --> I
  I --> F
  I --> D
  B --> M
  C1 --> L
  C2 --> L
  F --> L
  I --> J --> K
```

> **Notes:** The diagram is intentionally modular—components marked as optional (Kafka, Feast, Prometheus) are listed in the Ops and Phase sections and can be added in later phases.

---

## 3. Component Descriptions

### Data Sources

* **What:** Simulated or real IoT sensors, telemetry logs, maintenance records, external APIs.
* **Role:** Provide structured sensor time series and unstructured logs/reports.

### Data Ingestion (Prefect)

* **What:** Orchestrated ETL flows.
* **Responsibilities:** Pull/batch data, validate, transform, write to raw storage (S3/MinIO), and write processed rows to PostgreSQL.

### Storage

* **S3 / MinIO (Object Storage)** — stores raw files, processed Parquet, model artifacts, logs. Use `.csv` for raw snapshots, `.parquet` for processed features, `.json` for logs and metadata, and `.pkl`/`.onnx` for models.
* **PostgreSQL (Relational)** — stores normalized business tables, processed feature tables (for offline training), labels, and metadata used for analytics and quick queries.

### ML Pipeline

* **What:** Scripts and flows for feature engineering, model training, evaluation, and model selection.
* **Tools:** scikit-learn / PyTorch, MLflow for experiment tracking.

### Feature Store (optional)

* **What:** Feast or simple serving tables in PostgreSQL for online features.
* **Why:** Low-latency feature serving for real-time inference in production.

### Model Registry & Deployment

* **Model Registry:** MLflow or S3 path conventions to version models and artifacts.
* **Deployment:** FastAPI exposing REST endpoints, containerized with Docker. Could be deployed locally or to cloud (ECS / GKE / Cloud Run) later.

### Monitoring & Retraining

* **Monitoring:** MLflow metrics, Prefect flow health, Prometheus + Grafana for system & infra metrics.
* **Retraining pipeline:** Prefect flows that detect drift or performance degradation and trigger retraining, evaluation, and redeployment.

### Observability & Alerts

* **What:** Prometheus (metrics), Grafana (dashboards), and alerts through Slack/Email.

### Security & Governance

* **Secrets & Config:** `.env` for dev, Secrets Manager for cloud. Use IAM/roles for bucket/db access.
* **Data Governance:** Schema registry and data catalog (manual or automated) for discoverability and compatibility checks.

---

## 4. Data Storage & Formats

### Recommended storage mapping

* **PostgreSQL (structured, relational):**

  * `customer` / `asset` tables (primary keys)
  * `telemetry_aggregates` (downsampled features)
  * `labels` (failure events, RUL ground truth)
  * `feature_store` (offline features)

* **S3 / MinIO (raw / unstructured):**

  * `raw/` — original CSVs/JSONs from sources (immutable snapshots)
  * `processed/parquet/` — cleaned and engineered features in Parquet
  * `models/` — model artifacts (`.pkl`, `.pt`, `.onnx`) and model metadata
  * `logs/` — ingestion and pipeline logs (`.json`)

### Format recommendations

* **Raw snapshots:** CSV (small) or JSON (nested logs)
* **Processed feature tables:** Parquet (efficient for analytics)
* **Model artifacts:** Pickle (`.pkl`) for scikit-learn; Torch `.pt` or ONNX for portability
* **Metadata & logs:** JSON

---

## 5. Data Flow (End-to-end)

1. **Ingest:** Prefect flow reads simulated sensor data (CSV batches or API), validates schema, writes raw files to S3/MinIO and writes structured rows to a staging table in PostgreSQL.
2. **Transform:** ETL job loads staging rows, performs cleaning, feature extraction (e.g., rolling aggregates), and writes processed features to Parquet in S3 and joins/loads key feature tables to PostgreSQL.
3. **Train:** ML pipeline reads processed features (from Parquet or PostgreSQL), trains candidate models, logs experiments & metrics to MLflow, and registers best model.
4. **Deploy:** Model artifact pulled from MLflow/S3, containerized endpoint (FastAPI) serves predictions.
5. **Monitor:** Monitor prediction latency, throughput, and model performance (metrics). When drift or degradation detected, Prefect triggers retraining flow.
6. **Govern:** All data and model actions are logged for traceability and audit.

---

## 6. Security, Governance & SSHE considerations

* **Data Privacy & Access Control**

  * Use role-based access control for PostgreSQL and S3/MinIO buckets.
  * Mask or anonymize personally identifiable information (PII) in datasets used for experiments.
* **Secrets Management**

  * Dev: `.env` (gitignored) with python-dotenv
  * Prod: use cloud secrets (AWS Secrets Manager / GCP Secret Manager)
* **Encryption**

  * Enable server-side encryption for S3 and TLS for database connections.
* **Audit & Traceability**

  * Log pipeline runs, ETL steps, model changes, and access events. Store logs in `s3://.../logs/` or a centralized logging system.
* **SSHE & Environmental Compliance**

  * Document how model predictions reduce unsafe conditions (e.g., predicted failure triggers inspection), and keep logs/audit trails of actions taken.
  * Include safety checks in automated actions (e.g., require human-in-the-loop for critical maintenance decisions).

---

## 7. Observability, Monitoring & Retraining

* **What to monitor**

  * Data quality (missing rates, schema drift)
  * Model performance (accuracy, recall, precision, RUL error)
  * System health (container uptime, CPU/memory)
* **Tools**

  * Prefect UI for workflow monitoring
  * MLflow for experiments and model metrics
  * Prometheus + Grafana for production metrics and dashboards
  * Alerting via Slack / Email (via Grafana alerts)
* **Retraining policy (example)**

  * Retrain when model performance drops > X% compared to baseline OR when data drift detected in key features.
  * Prefect flow performs retraining: schedule → retrain → evaluate → if pass, register and deploy new model.

---

## 8. Implementation Phases & Roadmap (detailed)

### Phase 1 — Strategy & Setup (1 week)

**Focus:** Project charter, architecture, repo scaffold, base dev environment
**Outputs:** `project_charter.md`, `system_architecture.md`, repo scaffold, `docker-compose.yml` (Postgres + MinIO), `requirements.txt`, README

### Phase 2 — Data Engineering (2 weeks)

**Focus:** Ingestion flows, staging, storage
**Outputs:** Prefect flows for ingest, PostgreSQL schema, raw files in MinIO, processed Parquet outputs

### Phase 3 — Modeling (2 weeks)

**Focus:** Feature engineering, model experiments
**Outputs:** Training notebooks, MLflow experiments, registered model

### Phase 4 — Deployment (2 weeks)

**Focus:** Containerize model, expose FastAPI endpoint, local deployment
**Outputs:** Dockerized API, example client, README demo

### Phase 5 — Monitoring & MLOps (2 weeks)

**Focus:** Monitoring dashboards, automated retrain flow, model registry
**Outputs:** MLflow dashboards, Prefect retrain flows, alerts configured

### Phase 6 — Governance & Reporting (1 week)

**Focus:** Compliance documentation, SSHE alignment, business impact report
**Outputs:** Governance doc, cost/savings simulation, final README for portfolio

---

## 9. Deliverables for Phase 1

* `docs/project_charter.md` (one-page summary)
* `docs/system_architecture.md` (this file)
* `docs/ml_roadmap.md` (phase-by-phase plan)
* GitHub repo scaffold with folder layout
* `requirements.txt` or `environment.yml`
* `docker-compose.yml` with Postgres + MinIO definitions
* `.gitignore`, `.env.example`, and `README.md` starter
* ADR (`docs/decisions/adr-001-tool-selection.md`)

---

## 10. Project File Structure & Example Configs

### Recommended repo structure

```
AURA/
├── data/
│   ├── raw/
│   └── processed/
├── docs/
│   ├── project_charter.md
│   ├── system_architecture.md
│   └── ml_roadmap.md
├── src/
│   ├── ingestion/
│   ├── preprocessing/
│   ├── modeling/
│   ├── deployment/
│   └── utils/
├── notebooks/
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

### Example `.env.example`

```env
POSTGRES_USER=champ
POSTGRES_PASSWORD=supersecret123
POSTGRES_DB=ml_project
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ENDPOINT=minio:9000
S3_BUCKET=aura-bucket
```

### Example `docker-compose.yml` (minimal)

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:15
    env_file: .env
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  minio:
    image: minio/minio
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
volumes:
  pgdata:
```

---

## 11. Decisions & Tradeoffs

* **Prefect vs Airflow:** Prefect chosen for lower setup friction and modern developer ergonomics. Airflow is a stronger choice for very large teams or complex enterprise pipelines.
* **MinIO vs AWS S3:** MinIO for local dev reproducibility. When moving to prod, swap to AWS S3 or GCS using the same APIs.
* **PostgreSQL vs BigQuery / Redshift:** PostgreSQL chosen for ease of local dev and relational queries. For true scale use warehouse solutions.
* **MLflow vs other registries:** MLflow is easy to integrate and adequate for prototype. In production, consider platform-managed registry (SageMaker Model Registry or Vertex AI Model Registry).

---

## 12. Next Steps (actionable for Phase 1)

1. Create GitHub repo and push scaffold.
2. Add `docs/project_charter.md` and this `system_architecture.md`.
3. Create `.env.example`, `requirements.txt`, and `docker-compose.yml`.
4. Run `docker compose up -d` to confirm Postgres + MinIO boot.
5. Write a tiny Prefect flow: extract raw CSV into MinIO and write a row to PostgreSQL — run end-to-end.
6. Commit & open a PR (self-review) with Phase 1 deliverables.

---

*Document last updated:* 2025-10-26

> **Owner:** Komsan Kongwongsupak — ML Lead (Project: AURA)
