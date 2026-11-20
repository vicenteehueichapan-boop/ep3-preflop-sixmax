"""SSM solo contra la instancia nueva registrada y etiquetada por este proyecto."""
import argparse
import json
import time

from cloud import PREFIX, client, load

parser=argparse.ArgumentParser()
parser.add_argument('command',help='Comando de diagnostico o despliegue sobre NUESTRA instancia')
args=parser.parse_args()
state=load()
instance_id=state['instance_id']
instance=client('ec2').describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]
tags={t['Key']:t['Value'] for t in instance.get('Tags',[])}
if tags.get('Project')!=PREFIX or client('sts').get_caller_identity()['Account']!=state['account']:
    raise SystemExit('La instancia o cuenta no coincide con nuestro manifiesto. No se ejecuta nada.')
if instance_id in {i['id'] for i in state['protected_instances']}:
    raise SystemExit('Instancia de otro proyecto: operacion prohibida.')
ssm=client('ssm')
command=ssm.send_command(InstanceIds=[instance_id],DocumentName='AWS-RunShellScript',Parameters={'commands':[args.command]},TimeoutSeconds=600)['Command']['CommandId']
print('CommandId:',command,flush=True)
for _ in range(120):
    time.sleep(2)
    result=ssm.get_command_invocation(CommandId=command,InstanceId=instance_id)
    if result['Status'] not in ['Pending','InProgress','Delayed']:
        print(result.get('StandardOutputContent',''))
        print(result.get('StandardErrorContent',''))
        print('Status:',result['Status'])
        raise SystemExit(0 if result['Status']=='Success' else 1)
raise SystemExit('El comando sigue en curso. Consultar CommandId; no repetir una mutacion.')
