"""Entrena, selecciona por validacion y evalua una vez sobre el test reservado."""
import copy
import csv
import hashlib
import json
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from app.model import Classifier
from app.policy import ROOT, ACTIONS, all_hands, features, policy, reference


def main():
    torch.set_num_threads(1)
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    torch.use_deterministic_algorithms(True)
    out = ROOT / "artifacts"
    out.mkdir(exist_ok=True)
    hands = sorted(all_hands())
    assert len(hands) == len(set(hands)) == 169
    random.shuffle(hands)
    split_hands = {"train": hands[:118], "validation": hands[118:143], "test": hands[143:]}
    rows = [{"scenario": s, "hand": h, "action": reference(s, h), "split": split}
            for split, group in split_hands.items() for s in policy()["scenarios"] for h in group]
    with (ROOT / "data/dataset.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["scenario", "hand", "action", "split"])
        writer.writeheader()
        writer.writerows(rows)
    (ROOT / "data/splits.json").write_text(json.dumps(split_hands, indent=2), encoding="utf-8")
    def tensors(split):
        items = [r for r in rows if r["split"] == split]
        return (torch.tensor([features(r["scenario"], r["hand"]) for r in items], dtype=torch.float32),
                torch.tensor([ACTIONS.index(r["action"]) for r in items]))
    x, y = tensors("train")
    xv, yv = tensors("validation")
    xt, yt = tensors("test")
    for labels in (y, yv, yt):
        assert set(labels.tolist()) == {0, 1, 2}, "Cada particion debe cubrir las tres acciones"
    model = Classifier()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = torch.nn.CrossEntropyLoss(weight=1 / torch.bincount(y).float())
    best, best_epoch, stale = -1, 0, 0
    started = time.perf_counter()
    history = []
    generator = torch.Generator().manual_seed(42)
    for epoch in range(1, 401):
        model.train()
        order = torch.randperm(len(y), generator=generator)
        for batch in order.split(32):
            optimizer.zero_grad()
            loss = criterion(model(x[batch]), y[batch])
            loss.backward()
            optimizer.step()
        model.eval()
        with torch.inference_mode():
            pred = model(xv).argmax(1)
            score = f1_score(yv, pred, average="macro", zero_division=0)
        history.append({"epoch": epoch, "validation_macro_f1": float(score)})
        if score > best:
            best, best_epoch, stale = float(score), epoch, 0
            state = copy.deepcopy(model.state_dict())
        else:
            stale += 1
        if stale >= 60 and epoch >= 150:
            break
    model.load_state_dict(state)
    model.eval()
    with torch.inference_mode():
        raw_test = model(xt).argmax(1).tolist()
        logits = model(xt)
    test_rows = [r for r in rows if r["split"] == "test"]
    masked = logits.clone()
    for i, row in enumerate(test_rows):
        if row["scenario"] != "bb_vs_btn":
            masked[i, 1] = -float("inf")
    pred = masked.argmax(1).tolist()
    majority = {s: Counter(r["action"] for r in rows if r["split"] == "train" and r["scenario"] == s).most_common(1)[0][0] for s in policy()["scenarios"]}
    baseline = [ACTIONS.index(majority[r["scenario"]]) for r in test_rows]
    raw = json.dumps({k: v.tolist() for k, v in state.items()}, separators=(",", ":")).encode()
    sha = hashlib.sha256(raw).hexdigest()
    (out / "weights.json").write_bytes(raw)
    metadata = {"version": "preflop-" + sha[:10], "weights_sha256": sha,
        "policy_version": policy()["version"], "policy_sha256": hashlib.sha256((ROOT / "data/policy.json").read_bytes()).hexdigest(),
        "framework": "PyTorch " + torch.__version__, "architecture": [10, 32, 16, 3], "seed": 42,
        "learning_rate": 0.001, "optimizer": "Adam", "batch_size": 32, "max_epochs": 400,
        "epochs_executed": epoch, "selected_epoch": best_epoch, "validation_macro_f1": best,
        "training_seconds": time.perf_counter() - started, "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_records": len(rows), "split_counts": {s: len(group) * 6 for s, group in split_hands.items()},
        "purpose": "Imitacion supervisada de politica didactica propia. No GTO."}
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    metrics = {"environment": "local CPU", "model_version": metadata["version"], "n_test": len(pred),
        "accuracy": accuracy_score(yt, pred), "macro_f1": f1_score(yt, pred, average="macro", zero_division=0),
        "raw_macro_f1": f1_score(yt, raw_test, average="macro", zero_division=0),
        "raw_illegal_actions": sum(raw_test[i] == 1 and r["scenario"] != "bb_vs_btn" for i, r in enumerate(test_rows)),
        "classification_report": classification_report(yt, pred, labels=[0, 1, 2], target_names=ACTIONS, zero_division=0, output_dict=True),
        "confusion_matrix": confusion_matrix(yt, pred, labels=[0, 1, 2]).tolist(),
        "baseline_accuracy": accuracy_score(yt, baseline), "baseline_macro_f1": f1_score(yt, baseline, average="macro", zero_division=0),
        "per_scenario": {s: {"support": sum(r["scenario"] == s for r in test_rows), "accuracy": accuracy_score([int(yt[i]) for i,r in enumerate(test_rows) if r["scenario"] == s], [pred[i] for i,r in enumerate(test_rows) if r["scenario"] == s])} for s in policy()["scenarios"]}}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (out / "training_history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(json.dumps({**metadata, "test_accuracy": metrics["accuracy"], "test_macro_f1": metrics["macro_f1"], "baseline_macro_f1": metrics["baseline_macro_f1"]}, indent=2))


if __name__ == "__main__":
    main()
