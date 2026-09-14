"""Create the demo replication login without putting passwords in source or Terraform."""
import base64
import json
import secrets
from pathlib import Path
import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.cloud import storage

PROJECT = "data-enginner-job-app"
INSTANCE = "assessment-source-dev"
SECRET = "assessment-cdc-password"


def main():
    credentials, _ = google.auth.default()
    session = AuthorizedSession(credentials)
    root = f"https://secretmanager.googleapis.com/v1/projects/{PROJECT}/secrets/{SECRET}"
    existing = session.get(root, timeout=60)
    if existing.status_code == 404:
        response = session.post(root.rsplit("/", 1)[0], params={"secretId": SECRET}, json={"replication": {"automatic": {}}}, timeout=60)
        response.raise_for_status()
        password = secrets.token_urlsafe(32)
        response = session.post(root + ":addVersion", json={"payload": {"data": base64.b64encode(password.encode()).decode()}}, timeout=60)
        response.raise_for_status()
    else:
        existing.raise_for_status()
        response = session.get(root + "/versions/latest:access", timeout=60)
        response.raise_for_status()
        password = base64.b64decode(response.json()["payload"]["data"]).decode()
    response = session.post(f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{PROJECT}/instances/{INSTANCE}/users",
                            json={"name": "datastream", "password": password}, timeout=60)
    response.raise_for_status()
    print("Replication user operation:", response.json()["name"])
    sql = """CREATE TABLE IF NOT EXISTS orders (
      order_id integer PRIMARY KEY, customer_id integer NOT NULL,
      order_region text NOT NULL, order_date date NOT NULL,
      unit_price numeric(18,2) NOT NULL, quantity integer NOT NULL);
    INSERT INTO orders VALUES
      (201,1,'Yorkshire','2026-09-14',150,1),
      (202,2,'Tyne & Wear','2026-09-14',100,2),
      (203,3,'London','2026-09-14',350,4)
    ON CONFLICT (order_id) DO NOTHING;
    ALTER USER datastream WITH REPLICATION;
    GRANT CONNECT ON DATABASE shop TO datastream;
    GRANT USAGE ON SCHEMA public TO datastream;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO datastream;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO datastream;
    REVOKE cloudsqlsuperuser FROM datastream;
    DO $$ BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname='assessment_publication') THEN
        CREATE PUBLICATION assessment_publication FOR TABLE orders;
      END IF;
    END $$;
    """
    bucket = storage.Client(project=PROJECT).bucket(f"{PROJECT}-platform-demo")
    bucket.blob("source/setup.sql").upload_from_string(sql)
    # Cloud SQL's postgres user is not a true superuser. Create the slot as the
    # replication role in a second import after the grants have completed.
    bucket.blob("source/slot.sql").upload_from_string(
        "SET ROLE datastream; SELECT pg_create_logical_replication_slot('assessment_slot','pgoutput');")
    print("Uploaded source setup SQL (no password in SQL)")
    instance = session.get(f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{PROJECT}/instances/{INSTANCE}", timeout=60)
    instance.raise_for_status()
    path = Path("infra/platform-demo/terraform.tfvars.json")
    config = json.loads(path.read_text())
    config["source_ca"] = instance.json()["serverCaCert"]["cert"]
    path.write_text(json.dumps(config))

if __name__ == "__main__":
    main()
