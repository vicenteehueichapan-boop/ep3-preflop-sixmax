from locust import HttpUser, between, task


class Student(HttpUser):
    wait_time = between(.8, 1.2)

    def on_start(self):
        response = self.client.post('/v1/demo/session')
        response.raise_for_status()

    @task(5)
    def analyze(self):
        self.client.post('/v1/analyses', json={'scenario':'open_BTN','cards':['As','Kh'],'actions':[
            {'position':'UTG','action':'fold'}, {'position':'HJ','action':'fold'}, {'position':'CO','action':'fold'}]})

    @task
    def dashboard(self):
        self.client.get('/v1/dashboard')
