import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RANKS = "23456789TJQKA"
POSITIONS = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
ACTIONS = ["fold", "call", "raise"]


@lru_cache
def policy():
    return json.loads((ROOT / "data/policy.json").read_text(encoding="utf-8"))


def hand_parts(hand):
    if not re.fullmatch(r"[2-9TJQKA]{2}[so]?", hand):
        raise ValueError(f"Clase de mano invalida: {hand}")
    a, b = RANKS.index(hand[0]), RANKS.index(hand[1])
    pair = a == b
    if (pair and len(hand) != 2) or (not pair and (len(hand) != 3 or a < b)):
        raise ValueError(f"Clase no canonica: {hand}")
    return a, b, hand[2:] or "pair"


def all_hands():
    return [a + b + ("" if a == b else kind)
            for i, a in enumerate(RANKS) for b in RANKS[:i + 1]
            for kind in ([""] if a == b else ["s", "o"])]


def expand_range(expression):
    result = set()
    for token in filter(None, (x.strip() for x in expression.split(","))):
        if "-" in token:
            start, end = token.split("-")
            a, b, kind = hand_parts(start)
            c, d, other = hand_parts(end)
            if kind != other or (kind != "pair" and a != c):
                raise ValueError(f"Intervalo incompatible: {token}")
            if kind == "pair":
                result.update(RANKS[i] * 2 for i in range(min(a, c), max(a, c) + 1))
            else:
                result.update(RANKS[a] + RANKS[i] + kind for i in range(min(b, d), max(b, d) + 1))
        elif token.endswith("+"):
            a, b, kind = hand_parts(token[:-1])
            if kind == "pair":
                result.update(RANKS[i] * 2 for i in range(a, len(RANKS)))
            else:
                result.update(RANKS[a] + RANKS[i] + kind for i in range(b, a))
        else:
            hand_parts(token)
            result.add(token)
    return result


def canonical_cards(cards):
    if len(cards) != 2 or any(not re.fullmatch(r"[2-9TJQKA][shdc]", c) for c in cards):
        raise ValueError("Selecciona dos cartas validas (ejemplo As, Kh).")
    if cards[0] == cards[1]:
        raise ValueError("Las dos cartas deben ser diferentes.")
    a, b = sorted(cards, key=lambda c: RANKS.index(c[0]), reverse=True)
    return a[0] + b[0] + ("" if a[0] == b[0] else ("s" if a[1] == b[1] else "o"))


@lru_cache
def reference(scenario, hand):
    node = policy()["scenarios"][scenario]
    if hand in expand_range(node["raise"]):
        return "raise"
    if hand in expand_range(node["call"]):
        return "call"
    return "fold"


def features(scenario, hand):
    a, b, kind = hand_parts(hand)
    return [(a + 2) / 14, (b + 2) / 14, float(kind == "s"), float(kind == "pair")] + [
        float(s == scenario) for s in policy()["scenarios"]]


def expected_actions(scenario):
    hero = policy()["scenarios"][scenario]["hero"]
    result = []
    for position in POSITIONS[:POSITIONS.index(hero)]:
        if scenario == "bb_vs_btn" and position == "BTN":
            result.append({"position": position, "action": "raise", "raise_to_bb": 2.5})
        else:
            result.append({"position": position, "action": "fold"})
    return result


def state_for(scenario, cards, actions):
    if scenario not in policy()["scenarios"]:
        raise ValueError("Situacion fuera del catalogo preflop admitido.")
    hand = canonical_cards(cards)
    expected = expected_actions(scenario)
    if actions != expected:
        raise ValueError("La secuencia no corresponde al turno y situacion admitidos.")
    node = policy()["scenarios"][scenario]
    bets = {p: (0.5 if p == "SB" else 1.0 if p == "BB" else 0.0) for p in POSITIONS}
    for action in expected:
        if action["action"] == "raise":
            bets[action["position"]] = action["raise_to_bb"]
    return {"hand": hand, "hero": node["hero"], "pot_bb": sum(bets.values()),
            "to_call_bb": max(bets.values()) - bets[node["hero"]], "bets": bets,
            "legal_actions": ACTIONS if scenario == "bb_vs_btn" else ["fold", "raise"],
            "raise_to_bb": node["raise_to_bb"]}

