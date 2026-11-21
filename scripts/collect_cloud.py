"""Evidencia de lectura para recursos EP3. No exporta secretos ni configuraciones IAM."""
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runtime/evidence'
OUT.mkdir(parents=True,exist_ok=True)
REGION='us-east-1'
PREFIX='ep3-preflop'
now=datetime.now(timezone.utc)
sm=boto3.client('sagemaker',region_name=REGION)
scale=boto3.client('application-autoscaling',region_name=REGION)
cw=boto3.client('cloudwatch',region_name=REGION)
endpoint=sm.describe_endpoint(EndpointName=PREFIX)
report={'collected_at':now.isoformat(),'region':REGION,'endpoint':PREFIX,
    'status':endpoint['EndpointStatus'],'created_at':endpoint['CreationTime'].isoformat(),
    'variants':endpoint['ProductionVariants'],'metrics':{},'load':[]}
for name,stat in [('Invocations','Sum'),('Invocation4XXErrors','Sum'),('Invocation5XXErrors','Sum'),('ModelLatency','Average'),('OverheadLatency','Average')]:
    value=cw.get_metric_statistics(Namespace='AWS/SageMaker',MetricName=name,
        Dimensions=[{'Name':'EndpointName','Value':PREFIX},{'Name':'VariantName','Value':'main'}],
        StartTime=now-timedelta(minutes=45),EndTime=now,Period=60,Statistics=[stat])
    report['metrics'][name]=sorted(value['Datapoints'],key=lambda x:x['Timestamp'])
report['scalable_targets']=scale.describe_scalable_targets(ServiceNamespace='sagemaker',ResourceIds=['endpoint/'+PREFIX+'/variant/main'])['ScalableTargets']
report['scaling_activities']=scale.describe_scaling_activities(ServiceNamespace='sagemaker',ResourceId='endpoint/'+PREFIX+'/variant/main',ScalableDimension='sagemaker:variant:DesiredInstanceCount',MaxResults=20)['ScalingActivities']
report['scaling_policies']=scale.describe_scaling_policies(ServiceNamespace='sagemaker',ResourceId='endpoint/'+PREFIX+'/variant/main')['ScalingPolicies']
stats=OUT/'load-cloud_stats.csv'
if stats.exists():
    with stats.open(encoding='utf-8') as f:report['load']=list(csv.DictReader(f))
    report['load_profile']={
        'access_flow':'automatic_guest' if any(row['Name']=='/v1/demo/session' for row in report['load']) else 'legacy_oauth2',
        'host':'https://54.162.150.183' if any(row['Name']=='/v1/demo/session' for row in report['load']) else 'http://127.0.0.1:8000',
        'users':5,'configured_duration_seconds':300,'csv_modified_at':datetime.fromtimestamp(stats.stat().st_mtime,timezone.utc).isoformat()}
report['log_groups']=[]
logs=boto3.client('logs',region_name=REGION)
for prefix in ['/ep3-preflop/app','/aws/sagemaker/Endpoints/ep3-preflop']:
    for group in logs.describe_log_groups(logGroupNamePrefix=prefix)['logGroups']:
        report['log_groups'].append({k:group[k] for k in ['logGroupName','storedBytes','retentionInDays'] if k in group})
path=OUT/'cloud-metrics.json'
path.write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
summary={'collected_at':report['collected_at'],'endpoint_status':report['status'],'variants':report['variants'],
    'scaling_activities':[{k:a.get(k) for k in ['StatusCode','Description','Cause','StartTime','EndTime']} for a in report['scaling_activities']],
    'load':report['load'],'metric_points':{k:len(v) for k,v in report['metrics'].items()},'log_groups':report['log_groups']}
print(json.dumps(summary,indent=2,default=str))
