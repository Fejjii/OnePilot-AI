from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_response_shape(self, client: TestClient) -> None:
        data = client.get("/health").json()
        for key in ("app", "version", "env", "providers"):
            assert key in data, f"Missing key: {key}"
        assert isinstance(data["providers"], dict)
        providers = data["providers"]
        assert "gmail_configured" in providers
        assert "gmail_mode" in providers
        assert providers["gmail_send_enabled"] is False

    def test_health_content_type(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert "application/json" in resp.headers["content-type"]

    def test_health_request_id(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert "x-request-id" in resp.headers

        custom_id = "test-req-42"
        resp = client.get("/health", headers={"X-Request-ID": custom_id})
        assert resp.headers["x-request-id"] == custom_id
