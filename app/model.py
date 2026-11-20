import hashlib
import json
from pathlib import Path

import torch
from torch import nn

from app.policy import ACTIONS, ROOT, features


class Classifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(nn.Linear(10, 32), nn.ReLU(), nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, 3))

    def forward(self, x):
        return self.layers(x)


class Predictor:
    def __init__(self, directory=None):
        torch.set_num_threads(1)
        directory = Path(directory or ROOT / "artifacts")
        self.metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        raw = (directory / "weights.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != self.metadata["weights_sha256"]:
            raise ValueError("La integridad del modelo no coincide con su manifiesto.")
        self.model = Classifier()
        self.model.load_state_dict({k: torch.tensor(v) for k, v in json.loads(raw).items()})
        self.model.eval()

    def predict(self, scenario, hand):
        with torch.inference_mode():
            scores = self.model(torch.tensor([features(scenario, hand)], dtype=torch.float32)).softmax(dim=1)[0].tolist()
        legal = [0, 1, 2] if scenario == "bb_vs_btn" else [0, 2]
        raw_action = ACTIONS[max(range(3), key=lambda i: scores[i])]
        action = ACTIONS[max(legal, key=lambda i: scores[i])]
        return {"action": action, "raw_action": raw_action,
                "scores": dict(zip(ACTIONS, scores)), "model_version": self.metadata["version"]}

