import os
import secrets
import time
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
data_setting = Path(os.getenv('NINJA_DATA') or 'data')
DATA = (data_setting if data_setting.is_absolute() else ROOT / data_setting).resolve()
DATA.mkdir(parents=True, exist_ok=True)
ROOTS = [Path(p).resolve() for p in os.getenv('NINJA_ROOTS', '').split(';') if p]
# Only the origin the app is served from. Add http://127.0.0.1:5173 via NINJA_ORIGINS while running the Vite dev server.
ORIGINS = os.getenv('NINJA_ORIGINS', 'http://127.0.0.1:8000,http://localhost:8000').split(',')
token_file = DATA / 'access-token'
if not token_file.exists():
    token_file.write_text(secrets.token_urlsafe(32), encoding='utf-8')
TOKEN = os.getenv('NINJA_TOKEN') or token_file.read_text().strip()
if not TOKEN:
    raise RuntimeError('NINJA_TOKEN or data/access-token is empty; an empty token would let anyone in')

# Browser sessions get a random id in the cookie, never the master token: cookies reach every
# loopback port, and a lock/logout must be able to revoke them.
# ponytail: in-memory, so restarting the server signs browsers out until the page reloads.
SESSIONS: dict[str, float] = {}


def token_ok(value):
    return secrets.compare_digest((value or '').encode(), TOKEN.encode())


def new_session():
    sid = secrets.token_urlsafe(32)
    SESSIONS[sid] = time.time() + 86400
    return sid


def session_ok(sid):
    expires = SESSIONS.get(sid or '')
    return bool(expires and expires > time.time())

def approved_path(value: str, roots=None) -> Path:
    path = Path(value).resolve(strict=True)
    allowed = ROOTS if roots is None else roots
    if not any(path.is_relative_to(Path(r).resolve()) for r in allowed):
        raise ValueError('Path is outside approved folders')
    if not path.is_file():
        raise ValueError('Expected a regular file')
    return path

def artifact(project: str, name: str) -> Path:
    base = (DATA / 'projects' / project).resolve()
    path = (base / name).resolve()
    if not base.is_relative_to(DATA / 'projects') or not path.is_relative_to(base):
        raise ValueError('Invalid artifact path')
    return path
