"""Crea cinco alumnos sinteticos para medir concurrencia sin relajar rate limiting."""
from app.config import Settings
from app.db import User, database
from app.main import hasher

settings=Settings.from_env()
_,sessions=database(settings.database_url)
with sessions.begin() as session:
    for i in range(1,6):
        username='ep3-load'+str(i).zfill(2)
        if not session.get(User,username):
            session.add(User(id=username,password_hash=hasher.hash(settings.demo_password)))
print('Cinco alumnos sinteticos preparados; limites de seguridad sin cambios.')
