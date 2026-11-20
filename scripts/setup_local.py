import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    raise SystemExit(".env ya existe; no se sobrescriben credenciales.")
password = secrets.token_urlsafe(16)
target.write_text("\n".join([
    "APP_ENV=development", "MODEL_BACKEND=local", "EVENT_TRANSPORT=local",
    "DATABASE_URL=sqlite:///runtime/preflop.db", "DEMO_USERNAME=alumno",
    "DEMO_PASSWORD=" + password, "JWT_SECRET=" + secrets.token_hex(32), "RATE_LIMIT_PER_MINUTE=120", ""
]), encoding="utf-8")
os.chmod(target, 0o600)
print("Credenciales locales generadas en .env (excluido de Git).")
