import os
import time
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError
from dotenv import load_dotenv

load_dotenv()


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


JWT_SECRET_KEY = os.getenv("AUTH_JWT_SECRET") or os.getenv("AUTH_JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError("Missing required environment variable: AUTH_JWT_SECRET")

JWT_ISSUER         = os.getenv("AUTH_JWT_ISSUER")
JWT_AUDIENCE       = os.getenv("AUTH_JWT_AUDIENCE")
AUTH_JWT_ALGORITHM = os.getenv("AUTH_JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))


def hash_password(plain_password: str) -> str:
    """Genera el hash bcrypt. Retorna string UTF-8 para guardar en BD."""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica un password plano contra el hash bcrypt almacenado."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Firma el payload `data` como JWT.
    El caller (main.py/login) es responsable de incluir:
      - "sub":       str(player_id)
      - "player_id": int
      - "email":     str
      - "roles":     List[str]   ← lista, NO string singular
      - "type":      "user"
    """
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(minutes=JWT_EXPIRE_MINUTES)

    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})

    if JWT_ISSUER:
        to_encode["iss"] = JWT_ISSUER
    if JWT_AUDIENCE:
        to_encode["aud"] = JWT_AUDIENCE

    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=AUTH_JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decodifica y valida el JWT (alg + exp + opcional iss/aud).
    Lanza JWTError si el token es inválido o expirado.
    """
    options = {"verify_aud": JWT_AUDIENCE is not None}
    return jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[AUTH_JWT_ALGORITHM],
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        options=options,
    )


def get_token_remaining(payload: dict) -> dict:
    """
    Helper para GET /token/remaining.
    Recibe el payload ya decodificado y calcula segundos restantes.
    """
    exp = payload.get("exp", 0)
    iat = payload.get("iat", 0)
    now_ts = int(time.time())
    remaining = max(0, exp - now_ts)

    return {
        "expires_in_seconds": remaining,
        "expires_at": datetime.fromtimestamp(exp, tz=timezone.utc).isoformat(),
        "issued_at": (
            datetime.fromtimestamp(iat, tz=timezone.utc).isoformat() if iat else None
        ),
    }