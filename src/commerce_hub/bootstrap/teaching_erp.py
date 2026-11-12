"""Explicit teaching admission API/independent Worker. No acquisition on startup or recovery."""
import json
import os
from pathlib import Path
import sys
from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.entrypoints.http.app import create_app as app_factory
from commerce_hub.entrypoints.worker.__main__ import run
from commerce_hub.orchestration.service import HandlerSpec
from commerce_hub.scenarios.s01_teaching import TeachingS01AdmissionHandler


def registry(settings, projection=None):
    if settings.environment != "test" or settings.model_provider != "mock" or settings.model_network_enabled:
        raise ValueError("TEACHING_ADMISSION_REQUIRES_EXPLICIT_TEST_ENVIRONMENT")
    if projection is None:
        try:
            configured = os.environ.get("COMMERCE_TEACHING_PACKAGE_PATH")
            if not configured:
                raise ValueError("Explicit source package required")
            path = Path(configured)
            projection = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            raise ValueError("TEACHING_PACKAGE_NOT_AVAILABLE") from None
    handler = TeachingS01AdmissionHandler(projection)
    spec = HandlerSpec("TEACHING_S01_ADMISSION", "0.1.0", "s01.teaching.admission.v1." + handler.projection.revision[:32],
        handler, policy_version="teaching-admission-no-model-v1")
    return {spec.scenario_id:spec}


def create_app():
    settings = load_settings()
    return app_factory(settings,registry(settings))


if __name__ == "__main__":
    if sys.argv[1:] != ["worker"]:
        raise SystemExit("Use the explicit teaching admission worker command")
    settings = load_settings()
    raise SystemExit(run(settings,registry(settings)))
