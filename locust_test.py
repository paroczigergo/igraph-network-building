from locust import HttpLocust, TaskSet, task
"""
    This file is for testing the served endpoints
    with the https://locust.io/ testing tool
"""
class WebsiteTasks(TaskSet):
    def on_start(self):
        self.client.get("/graph/create")
    
    @task
    def get_from_redis(self):
        self.client.get("/graph/redis")

    @task
    def get_from_sqlite(self):
        self.client.get("/graph/sqlite")
        
    @task
    def search_from_sqlite(self):
        self.client.get("/search/sqlite?key=py")

    @task
    def search_from_igraph(self):
        self.client.get("/search/igraph?key=app.py")

class WebsiteUser(HttpLocust):
    task_set = WebsiteTasks
    min_wait = 5000
    max_wait = 15000