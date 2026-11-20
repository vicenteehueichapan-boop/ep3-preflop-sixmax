import json
import math

from app.policy import ACTIONS


class InferenceUnavailable(RuntimeError):
    pass


def validate_prediction(result):
    if result.get("action") not in ACTIONS or not result.get("model_version"):
        raise InferenceUnavailable("Respuesta del modelo invalida")
    scores = result.get("scores", {})
    if set(scores) != set(ACTIONS) or any(not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in scores.values()) or abs(sum(scores.values()) - 1) > 0.001:
        raise InferenceUnavailable("Puntuaciones invalidas")
    return result


class LocalInference:
    def __init__(self):
        from app.model import Predictor
        self.predictor = Predictor()

    def predict(self, scenario, hand):
        return validate_prediction(self.predictor.predict(scenario, hand))


class SageMakerInference:
    def __init__(self, settings):
        import boto3
        from botocore.config import Config
        self.endpoint = settings.endpoint_name
        self.client = boto3.client("sagemaker-runtime", region_name=settings.aws_region,
                                   config=Config(connect_timeout=3, read_timeout=8, retries={"total_max_attempts": 1}))

    def predict(self, scenario, hand):
        try:
            reply = self.client.invoke_endpoint(EndpointName=self.endpoint, ContentType="application/json",
                Body=json.dumps({"scenario": scenario, "hand": hand}).encode())
            return validate_prediction(json.loads(reply["Body"].read()))
        except InferenceUnavailable:
            raise
        except Exception as exc:
            raise InferenceUnavailable("El endpoint no esta disponible; intenta nuevamente.") from exc

