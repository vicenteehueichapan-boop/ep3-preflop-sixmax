"""Despliegue aislado. No contiene operaciones de eliminacion ni altera recursos ajenos."""
import argparse
import base64
import json
import os
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

import boto3

PREFIX = 'ep3-preflop'
ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'infra/state.json'
REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
TAGS = [{'Key':'Project','Value':PREFIX},{'Key':'Name','Value':PREFIX},{'Key':'Purpose','Value':'ITY1102-EP3'}]


def client(name):
    return boto3.client(name,region_name=REGION)


def save(state):
    STATE.write_text(json.dumps(state,indent=2,default=str),encoding='utf-8')


def load():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def prices():
    pricing=boto3.client('pricing',region_name='us-east-1')
    rates={}
    searches=[('ec2','AmazonEC2','t3.medium'),('sagemaker','AmazonSageMaker','ml.m5.large')]
    for key,service,instance in searches:
        filters=[{'Type':'TERM_MATCH','Field':'regionCode','Value':REGION},{'Type':'TERM_MATCH','Field':'instanceType','Value':instance}]
        if key=='ec2':
            filters += [{'Type':'TERM_MATCH','Field':k,'Value':v} for k,v in [('operatingSystem','Linux'),('tenancy','Shared'),('preInstalledSw','NA'),('capacitystatus','Used')]]
        items=pricing.get_products(ServiceCode=service,Filters=filters,MaxResults=100)
        found=[]
        for raw in items['PriceList']:
            product=json.loads(raw)
            attrs=product['product']['attributes']
            if key=='sagemaker' and 'host' not in attrs.get('usagetype','').lower():
                continue
            for term in product['terms']['OnDemand'].values():
                for dim in term['priceDimensions'].values():
                    if dim['unit']=='Hrs' and float(dim['pricePerUnit']['USD'])>0:
                        found.append(float(dim['pricePerUnit']['USD']))
        if not found:
            raise RuntimeError('No se obtuvo una tarifa verificable: '+key)
        rates[key]=max(found)
    rates['estimated_total_usd']=round(8*rates['ec2']+10*rates['sagemaker']+.48+.30+.30+.02,3)
    rates['includes']='8h EC2, 10h-instancia SageMaker, IPv4 96h, EBS/S3/logs/registro de imagen; sin Free Tier'
    if rates['estimated_total_usd']>4:
        raise RuntimeError('La estimacion supera USD 4 antes de contingencia; no se crean recursos: '+json.dumps(rates))
    return rates


def preflight():
    account=client('sts').get_caller_identity()['Account']
    ec2=client('ec2')
    existing=[{'id':i['InstanceId'],'name':next((t['Value'] for t in i.get('Tags',[]) if t['Key']=='Name'),'sin nombre'),'state':i['State']['Name']} for r in ec2.describe_instances()['Reservations'] for i in r['Instances']]
    role=client('iam').get_role(RoleName='LabRole')['Role']['Arn']
    profile=client('iam').get_instance_profile(InstanceProfileName='LabInstanceProfile')['InstanceProfile']['Arn']
    quotas=client('service-quotas').list_service_quotas(ServiceCode='sagemaker')['Quotas']
    # Quotas are paginated: exhaust them before checking the selected type.
    qclient=client('service-quotas')
    quotas=[]
    for page in qclient.get_paginator('list_service_quotas').paginate(ServiceCode='sagemaker'):
        quotas.extend(page['Quotas'])
    endpoint_quota=next(q['Value'] for q in quotas if q['QuotaName']=='ml.m5.large for endpoint usage')
    if endpoint_quota<2:
        raise RuntimeError('La cuota no permite verificar escalado de 1 a 2 instancias.')
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'account':account,'region':REGION,'role':role,'profile':profile,
        'protected_existing_instances':existing,'endpoint_quota':endpoint_quota,'prices':prices()}
    (ROOT/'infra/preflight.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    return report


def create_server():
    state=load()
    if state.get('instance_id'):
        print(json.dumps(state,indent=2));return
    report=preflight()
    ec2=client('ec2')
    vpcs=ec2.describe_vpcs(Filters=[{'Name':'is-default','Values':['true']}])['Vpcs']
    if not vpcs:
        raise RuntimeError('No hay VPC predeterminada; no se modifican redes existentes.')
    vpc=vpcs[0]['VpcId']
    subnet=sorted(ec2.describe_subnets(Filters=[{'Name':'vpc-id','Values':[vpc]},{'Name':'default-for-az','Values':['true']}])['Subnets'],key=lambda s:s['AvailabilityZone'])[0]['SubnetId']
    state.update({'account':report['account'],'region':REGION,'created_at':datetime.now(timezone.utc).isoformat(),'budget_usd':5,'protected_instances':report['protected_existing_instances']})
    save(state)
    if not state.get('security_group'):
        sg=ec2.create_security_group(GroupName=PREFIX,Description='Solo HTTPS y ACME para EP3 preflop',VpcId=vpc,TagSpecifications=[{'ResourceType':'security-group','Tags':TAGS}])['GroupId']
        state['security_group']=sg;save(state)
        ec2.authorize_security_group_ingress(GroupId=sg,IpPermissions=[{'IpProtocol':'tcp','FromPort':p,'ToPort':p,'IpRanges':[{'CidrIp':'0.0.0.0/0','Description':'HTTPS' if p==443 else 'ACME HTTP challenge'}]} for p in [80,443]])
    if not state.get('allocation_id'):
        address=ec2.allocate_address(Domain='vpc',TagSpecifications=[{'ResourceType':'elastic-ip','Tags':TAGS}])
        state.update({'allocation_id':address['AllocationId'],'public_ip':address['PublicIp']});save(state)
    ami=client('ssm').get_parameter(Name='/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64')['Parameter']['Value']
    bootstrap=(ROOT/'infra/bootstrap.sh').read_text().replace('__REGION__',REGION).replace('__PUBLIC_IP__',state['public_ip'])
    instance=ec2.run_instances(ImageId=ami,InstanceType='t3.medium',MinCount=1,MaxCount=1,
        ClientToken=PREFIX+'-server-v1',IamInstanceProfile={'Name':'LabInstanceProfile'},
        NetworkInterfaces=[{'DeviceIndex':0,'SubnetId':subnet,'Groups':[state['security_group']],'AssociatePublicIpAddress':True}],
        MetadataOptions={'HttpTokens':'required','HttpPutResponseHopLimit':2},CreditSpecification={'CpuCredits':'standard'},
        BlockDeviceMappings=[{'DeviceName':'/dev/xvda','Ebs':{'VolumeSize':20,'VolumeType':'gp3','Encrypted':True,'DeleteOnTermination':True}}],
        TagSpecifications=[{'ResourceType':'instance','Tags':TAGS},{'ResourceType':'volume','Tags':TAGS}],UserData=bootstrap)['Instances'][0]
    state['instance_id']=instance['InstanceId'];save(state)
    print(json.dumps({'instance_id':state['instance_id'],'public_ip':state['public_ip'],'status':'pending; bootstrap iniciara automaticamente'},indent=2))


def associate_ip():
    state=load();ec2=client('ec2')
    ec2.get_waiter('instance_running').wait(InstanceIds=[state['instance_id']])
    ec2.associate_address(InstanceId=state['instance_id'],AllocationId=state['allocation_id'])
    print('IPv4 asociada exclusivamente a '+state['instance_id'])


def deploy_model():
    # Runs on our EC2 under its existing instance profile, not on another project.
    account=client('sts').get_caller_identity()['Account']
    bucket=PREFIX+'-'+account+'-'+REGION
    s3=client('s3')
    try:
        s3.head_bucket(Bucket=bucket)
    except Exception:
        args={'Bucket':bucket}
        if REGION!='us-east-1':args['CreateBucketConfiguration']={'LocationConstraint':REGION}
        s3.create_bucket(**args)
    s3.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={k:True for k in ['BlockPublicAcls','IgnorePublicAcls','BlockPublicPolicy','RestrictPublicBuckets']})
    s3.put_bucket_encryption(Bucket=bucket,ServerSideEncryptionConfiguration={'Rules':[{'ApplyServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]})
    s3.put_bucket_tagging(Bucket=bucket,Tagging={'TagSet':TAGS})
    archive=ROOT/'runtime/model.tar.gz';archive.parent.mkdir(exist_ok=True)
    with tarfile.open(archive,'w:gz') as tar:
        for name in ['metadata.json','weights.json']:
            tar.add(ROOT/'artifacts'/name,arcname=name)
    s3.upload_file(str(archive),bucket,'artifacts/model.tar.gz')
    for name in ['policy.json','dataset.csv','splits.json']:
        s3.upload_file(str(ROOT/'data'/name),bucket,'data/'+name)
    sm=client('sagemaker')
    role=client('iam').get_role(RoleName='LabRole')['Role']['Arn']
    image=account+'.dkr.ecr.'+REGION+'.amazonaws.com/'+PREFIX+':1'
    existing={x['ModelName'] for x in sm.list_models(NameContains=PREFIX)['Models']}
    if PREFIX not in existing:
        sm.create_model(ModelName=PREFIX,ExecutionRoleArn=role,PrimaryContainer={'Image':image,'ModelDataUrl':'s3://'+bucket+'/artifacts/model.tar.gz'},Tags=TAGS)
    configs={x['EndpointConfigName'] for x in sm.list_endpoint_configs(NameContains=PREFIX)['EndpointConfigs']}
    if PREFIX not in configs:
        sm.create_endpoint_config(EndpointConfigName=PREFIX,ProductionVariants=[{'VariantName':'main','ModelName':PREFIX,'InitialInstanceCount':1,'InstanceType':'ml.m5.large','InitialVariantWeight':1}],Tags=TAGS)
    endpoints={x['EndpointName'] for x in sm.list_endpoints(NameContains=PREFIX)['Endpoints']}
    if PREFIX not in endpoints:
        sm.create_endpoint(EndpointName=PREFIX,EndpointConfigName=PREFIX,Tags=TAGS)
    print('Esperando endpoint SageMaker InService',flush=True)
    sm.get_waiter('endpoint_in_service').wait(EndpointName=PREFIX,WaiterConfig={'Delay':15,'MaxAttempts':60})
    scale=client('application-autoscaling')
    scale.register_scalable_target(ServiceNamespace='sagemaker',ResourceId='endpoint/'+PREFIX+'/variant/main',ScalableDimension='sagemaker:variant:DesiredInstanceCount',MinCapacity=1,MaxCapacity=2)
    scale.put_scaling_policy(PolicyName=PREFIX,ServiceNamespace='sagemaker',ResourceId='endpoint/'+PREFIX+'/variant/main',ScalableDimension='sagemaker:variant:DesiredInstanceCount',PolicyType='TargetTrackingScaling',TargetTrackingScalingPolicyConfiguration={'TargetValue':60,'PredefinedMetricSpecification':{'PredefinedMetricType':'SageMakerVariantInvocationsPerInstance'},'ScaleOutCooldown':60,'ScaleInCooldown':60})
    print('SageMaker listo y escalado 1..2 configurado',flush=True)


def status():
    state=load()
    result={'state':state}
    if state.get('instance_id'):
        instance=client('ec2').describe_instances(InstanceIds=[state['instance_id']])['Reservations'][0]['Instances'][0]
        result['instance_status']=instance['State']['Name']
    try:result['endpoint_status']=client('sagemaker').describe_endpoint(EndpointName=PREFIX)['EndpointStatus']
    except Exception as exc:result['endpoint_status']=type(exc).__name__
    print(json.dumps(result,indent=2,default=str))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['preflight','create-server','associate-ip','deploy-model','status'])
    args=parser.parse_args()
    {'preflight':preflight,'create-server':create_server,'associate-ip':associate_ip,'deploy-model':deploy_model,'status':status}[args.action]()
