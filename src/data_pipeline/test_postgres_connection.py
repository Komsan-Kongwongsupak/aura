import psycopg
from psycopg import sql

# Connection parameters (use the same as in your .env)
config = {
    "dbname": "ml_project",
    "user": "komsan",
    "password": "supersecret123",
    "host": "localhost",
    "port": "5432"
}

try:
    conn = psycopg.connect(**config)
    print("✅ Connected to PostgreSQL successfully!")

    with conn.cursor() as cur:
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print("PostgreSQL version:", version[0])

        cur.execute("CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY, note TEXT);")
        cur.execute("INSERT INTO test_table (note) VALUES ('Hello from Python!');")
        conn.commit()
        print("Inserted test row successfully!")

except Exception as e:
    print("❌ Connection failed:", e)
finally:
    if 'conn' in locals():
        conn.close()
        print("Connection closed.")
