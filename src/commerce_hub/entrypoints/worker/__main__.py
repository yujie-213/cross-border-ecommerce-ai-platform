import time
from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.bootstrap.composition import task_service
from commerce_hub.infrastructure.database import Database
from commerce_hub.orchestration.worker import Worker


def run(settings=None, registry=None):
    database = None
    try:
        settings = settings or load_settings()
        database = Database(settings)
        if not settings.auth_configured or not database.schema_ready():
            print("Worker not ready: configure trusted identity and run explicit migrations")
            return 1
        worker = Worker(task_service(database, settings, registry), settings.heartbeat_seconds)
        while True:
            if not worker.once():
                time.sleep(settings.poll_seconds)
    except KeyboardInterrupt:
        return 0
    except Exception:
        print("Worker stopped safely; recover using the same durable task and budget")
        return 1
    finally:
        if database:
            database.close()


if __name__ == "__main__":
    raise SystemExit(run())
