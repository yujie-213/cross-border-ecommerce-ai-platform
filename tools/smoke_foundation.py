"""Start an actual API process, check authorized DB readiness, then stop only that process."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from dotenv import dotenv_values
import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = {"scope": "A02_REAL_API_PROCESS_AND_AUTHORIZED_MYSQL", "status": "FAIL", "checks": [],
              "time": datetime.now(timezone.utc).isoformat(), "databaseWrites": 0, "erpCalls": 0, "modelCalls": 0}
    process = None
    logs = ""
    try:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "commerce_hub.entrypoints.http.app:create_app",
                                    "--factory", "--host", "127.0.0.1", "--port", str(port), "--no-access-log", "--no-server-header"],
                                   cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10, trust_env=False) as client:
            live = None
            for _ in range(100):
                if process.poll() is not None:
                    break
                try:
                    live = client.get("/health/live")
                    break
                except httpx.TransportError:
                    time.sleep(0.1)
            assert live is not None and live.status_code == 200
            report["checks"].append({"check": "real_process_live", "result": "PASS", "httpStatus": 200})
            response = client.get("/health/ready")
            body = response.json()
            assert response.status_code == 503 and body["code"] == "NOT_READY"
            assert body["details"]["database"] == "available"
            assert body["details"]["s01"] == "not_implemented"
            assert body["traceId"] == response.headers["X-Trace-Id"]
            report["checks"].append({"check": "real_mysql_connected_but_mvp_not_ready", "result": "PASS", "httpStatus": 503})
            for path in ["/api/v1/reports", "/api/v1/executions", "/api/v1/models"]:
                assert client.get(path).status_code == 404
            report["checks"].append({"check": "no_unimplemented_business_routes", "result": "PASS"})
            report["status"] = "PASS"
    except Exception:
        report["errorCode"] = "SMOKE_FAILED_NO_EXCEPTION_VALUES_RECORDED"
    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate(timeout=5)
            logs = (stdout + stderr).decode("utf-8", errors="replace")
            report["ownedApiProcessStopped"] = process.poll() is not None
        # Inspect in memory only. Never record logs or the password, even on failure.
        values = dotenv_values(ROOT / ".env", interpolate=False)
        secret = os.environ.get("S01_TEST_DB_PASSWORD", values.get("S01_TEST_DB_PASSWORD"))
        leaked = bool(secret and secret in logs)
        report["credentialLeakObserved"] = leaked
        if leaked:
            report["status"] = "FAIL"
            report["errorCode"] = "CREDENTIAL_LOGGING_FAILURE"
    safe_json = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(safe_json + "\n", encoding="utf-8")
    print(safe_json)
    return report["status"] != "PASS"


if __name__ == "__main__":
    raise SystemExit(main())
