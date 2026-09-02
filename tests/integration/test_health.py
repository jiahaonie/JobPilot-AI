"""健康检查 HTTP 端点测试。"""


def test_health_endpoint(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "JobPilot AI"
