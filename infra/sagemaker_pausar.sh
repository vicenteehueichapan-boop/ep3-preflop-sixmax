#!/bin/bash
# Pausa el cobro del endpoint SageMaker EP3 (ejecutar en AWS CloudShell, región us-east-1).
# Elimina SOLO el endpoint "ep3-preflop". Conserva el modelo, la configuración del endpoint,
# la imagen ECR y los artefactos S3, por lo que sagemaker_reanudar.sh lo recrea igual.
# No toca la EC2 ni recursos de otros proyectos.
set -euo pipefail
export AWS_DEFAULT_REGION=us-east-1
NAME=ep3-preflop
RESOURCE="endpoint/$NAME/variant/main"

if ! aws sagemaker describe-endpoint --endpoint-name "$NAME" >/dev/null 2>&1; then
  echo "El endpoint $NAME no existe: ya está pausado. No hay cobro de SageMaker."
  exit 0
fi

echo "1/2 Quitando el auto-scaling del endpoint $NAME..."
aws application-autoscaling deregister-scalable-target \
  --service-namespace sagemaker --resource-id "$RESOURCE" \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount 2>/dev/null || echo "    (no tenía auto-scaling registrado)"

echo "2/2 Eliminando el endpoint $NAME (se conservan modelo y configuración)..."
aws sagemaker delete-endpoint --endpoint-name "$NAME"
aws sagemaker wait endpoint-deleted --endpoint-name "$NAME"

echo "Listo: endpoint eliminado, SageMaker deja de cobrar."
echo "Conservados: modelo y configuración '$NAME' (verificación abajo)."
aws sagemaker describe-endpoint-config --endpoint-config-name "$NAME" --query 'EndpointConfigName' --output text
aws sagemaker describe-model --model-name "$NAME" --query 'ModelName' --output text
