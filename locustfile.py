import os
from locust import HttpUser, between, task


class Student(HttpUser):
    wait_time = between(.8, 1.2)

    def on_start(self):
        password = os.environ['DEMO_PASSWORD']
        response = self.client.post('/v1/auth/token', data={'username':os.getenv('DEMO_USERNAME','alumno'),'password':password})
        response.raise_for_status()
        self.client.headers['Authorization']='Bearer '+response.json()['access_token']

    @task(5)
    def analyze(self):
        self.client.post('/v1/analyses', json={'scenario':'open_BTN','cards':['As','Kh'],'actions':[
            {'position':'UTG','action':'fold'}, {'position':'HJ','action':'fold'}, {'position':'CO','action':'fold'}]})

    @task
    def dashboard(self):
        self.client.get('/v1/dashboard')
