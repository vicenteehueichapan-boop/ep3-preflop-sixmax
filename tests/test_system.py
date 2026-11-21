import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config import Settings
from app.db import Analysis, Outbox, ProcessedEvent, User, process_event
from app.inference import InferenceUnavailable, validate_prediction
from app.main import create_app, hasher
from app.model import Predictor
from app.policy import ROOT, all_hands, canonical_cards, expected_actions, expand_range, reference, state_for


@pytest.fixture
def client(tmp_path):
    settings = Settings(database_url='sqlite:///' + str(tmp_path/'test.db'), jwt_secret='test-secret-'*5,
        demo_password='testing-password-12345', rate_limit=1000)
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


def auth(client, username='alumno', password='testing-password-12345'):
    response = client.post('/v1/auth/token', data={'username': username, 'password': password})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def payload(scenario='open_BTN', cards=None):
    return {'scenario': scenario, 'cards': cards or ['As','Kh'], 'actions': expected_actions(scenario)}


def test_169_unique_classes():
    assert len(set(all_hands())) == 169


def test_range_boundaries_and_intervals():
    assert expand_range('77+') == {'77','88','99','TT','JJ','QQ','KK','AA'}
    assert expand_range('A2s-A5s') == {'A2s','A3s','A4s','A5s'}
    assert expand_range('KJs+') == {'KJs','KQs'}


def test_policy_known_decisions():
    assert reference('open_UTG','72o') == 'fold'
    assert reference('open_UTG','AA') == 'raise'
    assert reference('bb_vs_btn','99') == 'call'
    assert reference('bb_vs_btn','QQ') == 'raise'


def test_normalization_and_suit_equivalence():
    assert canonical_cards(['Kh','As']) == canonical_cards(['Ad','Kc']) == 'AKo'
    assert canonical_cards(['As','Ks']) == 'AKs'


def test_duplicate_cards_rejected():
    with pytest.raises(ValueError): canonical_cards(['As','As'])


def test_invalid_cards_rejected():
    with pytest.raises(ValueError): canonical_cards(['1s','Kh'])


def test_pot_and_bb_contribution():
    state = state_for('bb_vs_btn',['Ah','Kc'],expected_actions('bb_vs_btn'))
    assert state['pot_bb'] == 4 and state['to_call_bb'] == 1.5
    assert state['raise_to_bb'] == 10


def test_open_sb_pot():
    state = state_for('open_SB',['Ah','Kc'],expected_actions('open_SB'))
    assert state['pot_bb'] == 1.5 and state['to_call_bb'] == .5
    assert state['raise_to_bb'] == 3


def test_out_of_turn_rejected():
    with pytest.raises(ValueError): state_for('open_CO',['Ah','Kc'],[])


def test_unsupported_bb_walk_rejected():
    with pytest.raises(ValueError): state_for('open_BB',['Ah','Kc'],[])


def test_data_partitions_disjoint():
    parts=json.loads((ROOT/'data/splits.json').read_text())
    assert not set(parts['train'])&set(parts['test'])
    assert not set(parts['validation'])&set(parts['test'])
    assert not set(parts['train'])&set(parts['validation'])
    assert sum(map(len,parts.values())) == 169


def test_trained_model_and_metrics():
    model=Predictor()
    result=model.predict('open_UTG','AA')
    assert result['action']=='raise'
    assert sum(result['scores'].values())==pytest.approx(1,abs=1e-5)
    metrics=json.loads((ROOT/'artifacts/metrics.json').read_text())
    assert metrics['n_test']==156
    assert metrics['macro_f1']>=.85 and metrics['macro_f1']>metrics['baseline_macro_f1']


def test_invalid_model_scores_rejected():
    with pytest.raises(InferenceUnavailable):
        validate_prediction({'action':'raise','model_version':'x','scores':{'fold':float('nan'),'call':0,'raise':1}})


def test_login_invalid_credentials(client):
    assert client.post('/v1/auth/token',data={'username':'alumno','password':'incorrect'}).status_code==401


def test_anonymous_rejected(client):
    assert client.get('/v1/dashboard').status_code==401


def test_real_local_inference_and_persistence(client):
    headers=auth(client)
    response=client.post('/v1/analyses',headers=headers,json=payload())
    assert response.status_code==201, response.text
    value=response.json()
    assert value['action']=='raise' and value['source']=='local'
    assert value['request_id']==response.headers['X-Request-ID']
    restored=client.get('/v1/analyses/'+value['id'],headers=headers).json()
    assert restored['model_version']==value['model_version']
    stats=client.get('/v1/dashboard',headers=headers).json()
    assert stats['total']==stats['processed_events']==1


def test_api_duplicate_cards(client):
    assert client.post('/v1/analyses',headers=auth(client),json=payload(cards=['As','As'])).status_code==422


def test_api_invalid_sequence(client):
    body=payload();body['actions']=[]
    assert client.post('/v1/analyses',headers=auth(client),json=body).status_code==422


def test_user_isolation(client):
    headers=auth(client)
    value=client.post('/v1/analyses',headers=headers,json=payload()).json()
    with client.app.state.sessions.begin() as session:
        session.add(User(id='otro',password_hash=hasher.hash('second-user-password')))
    other=auth(client,'otro','second-user-password')
    assert client.get('/v1/analyses/'+value['id'],headers=other).status_code==404
    assert client.get('/v1/dashboard',headers=other).json()['total']==0


def test_endpoint_failure_no_fabricated_analysis(client):
    class Broken:
        def predict(self,*args):raise InferenceUnavailable('Endpoint no disponible')
    client.app.state.predictor=Broken()
    headers=auth(client)
    assert client.post('/v1/analyses',headers=headers,json=payload()).status_code==503
    assert client.get('/v1/dashboard',headers=headers).json()['total']==0


def test_rate_limit(client):
    headers=auth(client)
    client.app.state.settings.rate_limit=2
    assert client.get('/v1/catalog',headers=headers).status_code==200
    assert client.get('/v1/catalog',headers=headers).status_code==200
    assert client.get('/v1/catalog',headers=headers).status_code==429


def test_event_idempotence(client):
    value=client.post('/v1/analyses',headers=auth(client),json=payload()).json()
    with client.app.state.sessions.begin() as session:
        assert process_event(session,value['event_id']) is False
        assert session.scalar(select(func.count()).select_from(ProcessedEvent))==1


def test_durable_outbox_without_broker(client):
    client.app.state.settings.event_transport='rabbitmq'
    value=client.post('/v1/analyses',headers=auth(client),json=payload()).json()
    with client.app.state.sessions() as session:
        event=session.get(Outbox,value['event_id'])
        assert event and not event.published and not event.processed


def test_comparison_explains_position_changes(client):
    value=client.get('/v1/comparison?card1=As&card2=5s',headers=auth(client)).json()
    assert len(value['comparisons'])==6
    assert len({x['reference_action'] for x in value['comparisons']})>1


def test_openapi_and_health(client):
    schema=client.get('/openapi.json').json()
    assert '/v1/analyses' in schema['paths']
    assert 'security' in schema['paths']['/v1/analyses']['post']
    assert client.get('/health/ready').status_code==200


def test_production_rejects_local_substitutions():
    with pytest.raises(ValueError):
        Settings(database_url='sqlite:///x.db',jwt_secret='a'*40,demo_password='b'*16,environment='production').validate()


def test_guest_session_opens_table_without_credentials(client):
    response=client.post('/v1/demo/session')
    assert response.status_code==200
    assert response.json()=={'session_type':'guest','expires_in':1800}
    cookie=response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=strict' in cookie and 'max-age=1800' in cookie
    assert client.get('/v1/catalog').status_code==200
    result=client.post('/v1/analyses',json=payload())
    assert result.status_code==201 and result.json()['action']=='raise'


def test_guest_reload_reuses_history(client):
    client.post('/v1/demo/session')
    identity=client.get('/v1/catalog').json()['username']
    client.post('/v1/analyses',json=payload())
    client.post('/v1/demo/session')
    assert client.get('/v1/catalog').json()['username']==identity
    assert client.get('/v1/dashboard').json()['total']==1


def test_guest_browsers_do_not_share_histories(client):
    client.post('/v1/demo/session')
    identity=client.get('/v1/catalog').json()['username']
    result=client.post('/v1/analyses',json=payload()).json()
    client.cookies.clear()
    client.post('/v1/demo/session')
    assert client.get('/v1/catalog').json()['username']!=identity
    assert client.get('/v1/dashboard').json()['total']==0
    assert client.get('/v1/analyses/'+result['id']).status_code==404


def test_guest_cookie_rejects_cross_origin_writes(client):
    assert client.post('/v1/demo/session',headers={'Origin':'https://other.example'}).status_code==403
    client.post('/v1/demo/session')
    assert client.post('/v1/analyses',headers={'Origin':'https://other.example'},json=payload()).status_code==403
    assert client.post('/v1/analyses',headers={'Origin':'http://testserver'},json=payload()).status_code==201


def test_guest_tampered_cookie_is_rejected_and_replaced(client):
    client.cookies.set('preflop_demo','tampered',domain='testserver.local',path='/')
    assert client.get('/v1/dashboard').status_code==401
    assert client.post('/v1/demo/session').status_code==200
    assert client.get('/v1/dashboard').status_code==200


def test_guest_session_creation_rate_limit(client):
    for _ in range(20):assert client.post('/v1/demo/session').status_code==200
    assert client.post('/v1/demo/session').status_code==429


def test_guest_has_no_password_login(client):
    client.post('/v1/demo/session')
    identity=client.get('/v1/catalog').json()['username']
    assert client.post('/v1/auth/token',data={'username':identity,'password':'anything'}).status_code==401
