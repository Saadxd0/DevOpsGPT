import os
from fastapi.testclient import TestClient
import importlib.util
from pathlib import Path


def test_app_boots_and_serves_docs():
    # Mock GEMINI_API_KEY if not set, to allow the app to boot during tests
    if not os.environ.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = "mock_key_for_testing"

    module_path = Path(__file__).resolve().parents[1] / "main.py"
    spec = importlib.util.spec_from_file_location("backend_main", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    client = TestClient(module.app)
    response = client.get("/docs")

    assert response.status_code == 200
