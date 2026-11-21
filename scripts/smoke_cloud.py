"""Prueba HTTP real. Ejecutar dentro del contenedor API, sin imprimir credenciales."""
import json
import os
import time
from pathlib import Path

import httpx


def main():
    base=os.getenv('BASE_URL','https://54.162.150.183')
    results=[]
    with httpx.Client(base_url=base,timeout=30,trust_env=False) as c:
        def check(name,condition,details=None):
            results.append({'case':name,'passed':bool(condition),'details':details})
        check('health_live',c.get('/health/live').status_code==200)
        ready=c.get('/health/ready');check('cloud_dependencies',ready.status_code==200,ready.json())
        check('anonymous_rejected',c.get('/v1/dashboard').status_code==401)
        check('bad_password',c.post('/v1/auth/token',data={'username':os.environ['DEMO_USERNAME'],'password':'not-correct'}).status_code==401)
        opened=c.post('/v1/demo/session')
        check('guest_session_without_password',opened.status_code==200)
        opened.raise_for_status()
        flags=opened.headers.get('set-cookie','').lower()
        check('secure_httponly_cookie','secure' in flags and 'httponly' in flags and 'samesite=strict' in flags)
        check('no_token_in_response','access_token' not in opened.json())
        catalog=c.get('/v1/catalog').json()
        visitor=catalog['username']
        c.post('/v1/demo/session')
        check('guest_session_reused',c.get('/v1/catalog').json()['username']==visitor)
        check('sagemaker_enabled',catalog['model_backend']=='sagemaker')
        check('rabbitmq_enabled',catalog['event_transport']=='rabbitmq')
        check('catalog_6_spots',len(catalog['scenarios'])==6)
        examples=[('open_UTG',['7s','2h'],'fold'),('open_BTN',['As','Kh'],'raise'),('bb_vs_btn',['9s','9h'],'call')]
        analysis_ids=[]
        for scenario,cards,expected in examples:
            actions=next(s['actions'] for s in catalog['scenarios'] if s['id']==scenario)
            body={'scenario':scenario,'cards':cards,'actions':actions}
            response=c.post('/v1/analyses',json=body)
            check('analysis_'+expected,response.status_code==201,response.status_code)
            response.raise_for_status();value=response.json();analysis_ids.append(value['id'])
            check('real_prediction_'+expected,value['action']==expected and value['source']=='sagemaker',{'action':value['action'],'version':value['model_version'],'inference_ms':value['inference_ms']})
            restored=c.get('/v1/analyses/'+value['id'])
            check('history_'+expected,restored.status_code==200 and restored.json()['request_id']==value['request_id'])
        actions=next(s['actions'] for s in catalog['scenarios'] if s['id']=='open_BTN')
        check('duplicate_cards',c.post('/v1/analyses',json={'scenario':'open_BTN','cards':['As','As'],'actions':actions}).status_code==422)
        check('out_of_turn',c.post('/v1/analyses',json={'scenario':'open_BTN','cards':['As','Kh'],'actions':[]}).status_code==422)
        check('cross_origin_rejected',c.post('/v1/analyses',headers={'Origin':'https://other.example'},json={'scenario':'open_BTN','cards':['As','Kh'],'actions':actions}).status_code==403)
        comparison=c.get('/v1/comparison?card1=As&card2=5s')
        check('comparison',comparison.status_code==200 and len(comparison.json()['comparisons'])==6)
        for _ in range(15):
            stats=c.get('/v1/dashboard').json()
            if stats['processed_events']==stats['total']:break
            time.sleep(1)
        check('rabbitmq_consumed',stats['processed_events']==stats['total'],{'total':stats['total'],'processed':stats['processed_events']})
        check('openapi', '/v1/analyses' in c.get('/openapi.json').json()['paths'])
        with httpx.Client(base_url=base,timeout=30,trust_env=False) as other:
            other.post('/v1/demo/session').raise_for_status()
            check('guest_history_isolated',other.get('/v1/dashboard').json()['total']==0)
            check('guest_cannot_read_other_analysis',other.get('/v1/analyses/'+analysis_ids[0]).status_code==404)
    report={'base_url':base,'environment':'AWS real','tests':results,'passed':sum(r['passed'] for r in results),'total':len(results)}
    out=Path(os.getenv('EVIDENCE_DIR','/tmp/ep3-evidence'));out.mkdir(parents=True,exist_ok=True)
    (out/'cloud-smoke.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    if not all(r['passed'] for r in results):raise SystemExit(1)


if __name__=='__main__':main()
