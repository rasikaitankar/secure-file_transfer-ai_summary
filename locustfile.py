from locust import HttpUser, task, between

class FileShareUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login before starting tasks"""
        self.client.post("/login", json={
            "username": "alice",
            "password": "alice123"
        })

    @task(3)
    def upload_file(self):
        """Test file upload"""
        with open("test.txt", "rb") as f:
            self.client.post(
                "/upload",
                files={"file": f},
                data={"receiver_id": "bob"}
            )

    @task(2)
    def get_files(self):
        """Fetch files for user"""
        self.client.get("/files/bob")

    @task(1)
    def get_stats(self):
        """Check server stats"""
        self.client.get("/stats")

    @task(1)
    def health_check(self):
        self.client.get("/health")