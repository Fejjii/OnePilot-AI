"""Tests for the document service and `/documents/*` endpoints."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient


def _register(client: TestClient, *, suffix: str) -> dict:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"docs{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Docs User",
            "organization_name": f"DocsOrg{suffix}",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _upload(
    client: TestClient,
    token: str,
    *,
    filename: str,
    content: bytes,
    content_type: str = "text/markdown",
) -> dict:
    files = {"file": (filename, io.BytesIO(content), content_type)}
    resp = client.post("/documents/upload", files=files, headers=_auth_headers(token))
    if resp.status_code != 200:
        return {"_status": resp.status_code, "_body": resp.text}
    return resp.json()


class TestDocumentUpload:
    def test_upload_markdown(self, client: TestClient) -> None:
        token = _register(client, suffix="_upmd")["access_token"]
        body = _upload(
            client,
            token,
            filename="policy.md",
            content=b"# Policy\n\nAll customer data is encrypted at rest.",
        )
        assert "id" in body
        assert body["filename"] == "policy.md"
        assert body["title"] == "Policy"
        assert body["chunk_count"] >= 1
        assert body["status"] == "ready"

    def test_upload_rejects_unsupported_type(self, client: TestClient) -> None:
        token = _register(client, suffix="_upbad")["access_token"]
        files = {"file": ("photo.png", io.BytesIO(b"\x89PNG\r\n"), "image/png")}
        resp = client.post("/documents/upload", files=files, headers=_auth_headers(token))
        assert resp.status_code == 422

    def test_upload_creates_chunks(self, client: TestClient) -> None:
        token = _register(client, suffix="_upchunks")["access_token"]
        long_text = b"# Big Doc\n\n" + b"Paragraph line.\n\n" * 200
        body = _upload(client, token, filename="big.md", content=long_text)
        assert body["chunk_count"] > 1


class TestDocumentList:
    def test_list_returns_uploaded(self, client: TestClient) -> None:
        token = _register(client, suffix="_list")["access_token"]
        _upload(client, token, filename="a.md", content=b"# A\nalpha content")
        _upload(client, token, filename="b.md", content=b"# B\nbravo content")
        resp = client.get("/documents", headers=_auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2
        titles = {item["title"] for item in body["items"]}
        assert {"A", "B"} <= titles


class TestDocumentGet:
    def test_get_document_with_chunks(self, client: TestClient) -> None:
        token = _register(client, suffix="_get")["access_token"]
        created = _upload(
            client, token, filename="faq.md", content=b"# FAQ\n\nQuestion one body."
        )
        resp = client.get(
            f"/documents/{created['id']}?include_chunks=true",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == created["id"]
        assert len(body["chunks"]) >= 1

    def test_get_unknown_document_returns_404(self, client: TestClient) -> None:
        token = _register(client, suffix="_get404")["access_token"]
        resp = client.get("/documents/doc_does_not_exist", headers=_auth_headers(token))
        assert resp.status_code == 404


class TestDocumentDelete:
    def test_delete_document(self, client: TestClient) -> None:
        token = _register(client, suffix="_del")["access_token"]
        created = _upload(client, token, filename="byebye.md", content=b"# Bye\nlater")
        resp = client.delete(
            f"/documents/{created['id']}", headers=_auth_headers(token)
        )
        assert resp.status_code == 204
        gone = client.get(
            f"/documents/{created['id']}", headers=_auth_headers(token)
        )
        assert gone.status_code == 404


class TestDocumentTenantIsolation:
    def test_other_tenant_cannot_see_documents(self, client: TestClient) -> None:
        token_a = _register(client, suffix="_isoA")["access_token"]
        token_b = _register(client, suffix="_isoB")["access_token"]
        created = _upload(
            client, token_a, filename="secret.md", content=b"# Secret\ninternal data"
        )

        resp = client.get(
            f"/documents/{created['id']}", headers=_auth_headers(token_b)
        )
        assert resp.status_code == 404

        listing = client.get("/documents", headers=_auth_headers(token_b))
        assert listing.json()["total"] == 0
