import uuid

from locust import HttpUser, between, task


class SmokeUser(HttpUser):
    """轻量级压力测试：覆盖无需外部 API 的核心接口。"""

    wait_time = between(0.5, 2)

    def on_start(self):
        self.uid = uuid.uuid4().hex[:8]
        self.client.post(
            "/api/auth/register",
            json={
                "email": f"locust_{self.uid}@example.com",
                "username": f"locust_{self.uid}",
                "password": "Locust1234",
            },
        )
        resp = self.client.post(
            "/api/auth/login",
            json={"email": f"locust_{self.uid}@example.com", "password": "Locust1234"},
        )
        self.token = resp.json().get("access_token") if resp.status_code == 200 else None

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(2)
    def me(self):
        if self.token:
            self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {self.token}"})

    @task(1)
    def openapi(self):
        self.client.get("/openapi.json")
