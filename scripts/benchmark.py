"""Mide la misma inferencia con carga por peticion y con instancia reutilizada."""
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.model import Predictor
from app.policy import ROOT


def summary(values):
    values=sorted(values)
    def percentile(q):return values[min(len(values)-1,int((len(values)-1)*q))]
    return {'samples':len(values),'p50_ms':percentile(.5),'p95_ms':percentile(.95),'p99_ms':percentile(.99),'mean_ms':statistics.mean(values)}


def main():
    warm=Predictor();warm.predict('open_BTN','AKo')
    cold_times=[];warm_times=[]
    for _ in range(100):
        t=time.perf_counter();Predictor().predict('open_BTN','AKo');cold_times.append((time.perf_counter()-t)*1000)
        t=time.perf_counter();warm.predict('open_BTN','AKo');warm_times.append((time.perf_counter()-t)*1000)
    result={'environment':'local CPU','scenario':'open_BTN','hand':'AKo','model_version':warm.metadata['version'],
        'load_per_request':summary(cold_times),'preloaded_model':summary(warm_times),
        'mean_speedup':statistics.mean(cold_times)/statistics.mean(warm_times),
        'limitation':'Microbenchmark de inferencia local; no es latencia de red ni de AWS.'}
    (ROOT/'artifacts/optimization-local.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
