from locust import HttpUser, task, between


class JanusUser(HttpUser):
    wait_time = between(0.2, 1.0)

    @task(3)
    def recall(self):
        params = {"query": "arquitetura do sistema", "limit": 5}
        self.client.get("/api/v1/memory/recall", params=params, name="memory_recall")

    @task(1)
    def memorize(self):
        payload = {
            "type": "knowledge_event",
            "content": "Teste de memorizacao de evento",
            "metadata": {"origin": "load_test"},
        }
        self.client.post("/api/v1/memory/memorize", json=payload, name="memory_memorize")
