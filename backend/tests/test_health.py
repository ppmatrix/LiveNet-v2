def test_health_returns_200(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200


def test_health_returns_expected_payload(client):
    response = client.get("/api/v1/health")

    assert response.json == {
        "status": "ok",
        "service": "livenet-api",
    }


def test_unknown_endpoint_returns_404(client):
    response = client.get("/api/v1/unknown")

    assert response.status_code == 404
