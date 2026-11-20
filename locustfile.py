import os
from itertools import cycle
from locust import HttpUser, between, task

users = cycle(range(1,6))


class Student(HttpUser):
    wait_time = between(.8, 1.2)

    def on_start(self):
        password = os.environ['DEMO_PASSWORD']
        username = os.getenv('DEMO_USERNAME','alumno')
        if os.getenv('LOAD_USER_PREFIX'):
            username = os.environ['LOAD_USER_PREFIX'] + str(next(users)).zfill(2)
        response = self.client.post('/v1/auth/token', data={'username':username,'password':password})
        response.raise_for_status()
        self.client.headers['Authorization']='Bearer '+response.json()['access_token']

    @task(5)
    def analyze(self):
        self.client.post('/v1/analyses', json={'scenario':'open_BTN','cards':['As','Kh'],'actions':[
            {'position':'UTG','action':'fold'}, {'position':'HJ','action':'fold'}, {'position':'CO','action':'fold'}]})

    @task
    def dashboard(self):
        self.client.get('/v1/dashboard')
