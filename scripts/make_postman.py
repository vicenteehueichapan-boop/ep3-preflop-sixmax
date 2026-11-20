"""Genera colección sin credenciales; rellenar demoPassword solo en el cliente privado."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def request(name,method,path,body=None):
    r={'method':method,'header':[],'url':'{{baseUrl}}'+path}
    if body is not None:r['body']={'mode':'raw','raw':json.dumps(body,indent=2),'options':{'raw':{'language':'json'}}}
    return {'name':name,'request':r}

items=[{'name':'1 Sesión privada','request':{'method':'POST','url':'{{baseUrl}}/v1/auth/token','auth':{'type':'noauth'},'body':{'mode':'urlencoded','urlencoded':[{'key':'username','value':'{{demoUsername}}'},{'key':'password','value':'{{demoPassword}}'}]}},'event':[{'listen':'test','script':{'type':'text/javascript','exec':['pm.test("Inicio de sesión", () => pm.response.to.have.status(200));','if(pm.response.code === 200) pm.collectionVariables.set("token", pm.response.json().access_token);']}}]},request('2 Catálogo','GET','/v1/catalog')]
spots=[('Fold UTG','open_UTG',['7s','2h'],[]),('Raise BTN','open_BTN',['As','Kh'],[{'position':p,'action':'fold'} for p in ['UTG','HJ','CO']]),('Call BB','bb_vs_btn',['9s','9h'],[{'position':p,'action':'fold'} for p in ['UTG','HJ','CO']]+[{'position':'BTN','action':'raise','raise_to_bb':2.5},{'position':'SB','action':'fold'}])]
for name,spot,cards,actions in spots:items.append(request(name,'POST','/v1/analyses',{'scenario':spot,'cards':cards,'actions':actions}))
items.extend([request('Historial y eventos','GET','/v1/dashboard'),request('Comparación entre posiciones','GET','/v1/comparison?card1=As&card2=5s')])
collection={'info':{'name':'EP3 Preflop Six Max','description':'Demo académica real en AWS. Introducir la contraseña solo en variable privada del cliente. No exportar ni sincronizar variables rellenadas. Las recomendaciones imitan una política didáctica, no GTO.','schema':'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},'auth':{'type':'bearer','bearer':[{'key':'token','value':'{{token}}','type':'string'}]},'variable':[{'key':'baseUrl','value':'https://54.162.150.183'},{'key':'demoUsername','value':'alumno'},{'key':'demoPassword','value':''},{'key':'token','value':''}],'item':items}
path=ROOT/'docs/EP3_Postman.collection.json';path.write_text(json.dumps(collection,indent=2,ensure_ascii=False),encoding='utf-8');print(path)
