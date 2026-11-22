#!/bin/bash
# Recrea el endpoint SageMaker EP3 desde su configuración guardada (ejecutar en AWS CloudShell).
# Tarda ~5-10 minutos. Vuelve a registrar el auto-scaling 1-2 instancias (60 invocaciones/instancia/min).
set -euo pipefail
export AWS_DEFAULT_REGION=us-east-1
NAME=ep3-preflop
RESOURCE="endpoint/$NAME/variant/main"

STATUS=$(aws sagemaker describe-endpoint --endpoint-name "$NAME" --query EndpointStatus --output text 2>/dev/null || echo "NoExiste")
if [ "$STATUS" = "NoExiste" ]; then
  echo "1/3 Creando endpoint $NAME desde la configuración guardada..."
  aws sagemaker create-endpoint --endpoint-name "$NAME" --endpoint-config-name "$NAME" \
    --tags Key=Project,Value=$NAME Key=Name,Value=$NAME Key=Purpose,Value=ITY1102-EP3 >/dev/null
else
  echo "1/3 El endpoint ya existe (estado: $STATUS)."
fi

echo "2/3 Esperando InService (5-10 minutos)..."
aws sagemaker wait endpoint-in-service --endpoint-name "$NAME"

echo "3/3 Registrando auto-scaling 1-2 instancias..."
aws application-autoscaling register-scalable-target \
  --service-namespace sagemaker --resource-id "$RESOURCE" \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount --min-capacity 1 --max-capacity 2
aws application-autoscaling put-scaling-policy --policy-name "$NAME" \
  --service-namespace sagemaker --resource-id "$RESOURCE" \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":60,"PredefinedMetricSpecification":{"PredefinedMetricType":"SageMakerVariantInvocationsPerInstance"},"ScaleOutCooldown":60,"ScaleInCooldown":60}' >/dev/null

echo "Listo: $NAME InService. Comprueba https://54.162.150.183/health/ready"
