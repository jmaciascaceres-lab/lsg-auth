from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text

from .db import Base, engine, get_db
from . import models, schemas
from .auth import hash_password, verify_password, create_access_token, decode_access_token

app = FastAPI(
    title="LifeSync-Games Auth Service",
    version="1.0.0",
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


@app.on_event("startup")
def on_startup():
    # Crea tablas si no existen (no tocará las columnas existentes)
    Base.metadata.create_all(bind=engine)


# ========= Endpoints =========

@app.get("/health")
def healthcheck(db: Session = Depends(get_db)):
    """
    Healthcheck simple. Intenta hacer SELECT 1 en MySQL.
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"DB error: {e}",
        )


@app.post(
    "/players",
    response_model=schemas.PlayerOut,
    status_code=status.HTTP_201_CREATED,
)
def create_player(
    player_in: schemas.PlayerCreate,
    db: Session = Depends(get_db),
):
    # hash de la contraseña
    pw_hash = hash_password(player_in.password)

    player = models.Player(
        name=player_in.name,
        email=player_in.email,
        password_hash=pw_hash,
        age=player_in.age,
        role=player_in.role,
    )

    db.add(player)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        # Principalmente conflicto de email UNIQUE
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo crear el jugador: {e}",
        )

    db.refresh(player)
    return player


@app.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login OAuth2: Swagger enviará username+password como formulario.
    Usamos username como si fuera el email del jugador.
    """
    # En este diseño, username == email
    player = (
        db.query(models.Player)
        .filter(models.Player.email == form_data.username)
        .first()
    )

    if not player or not verify_password(form_data.password, player.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )

    claims = {
        "sub": str(player.id_players),
        "player_id": int(player.id_players),
        "email": player.email,
        "role": player.role,           # <- CRÍTICO
        "type": "user",
    }
    access_token = create_access_token(claims)
    return schemas.Token(access_token=access_token, token_type="bearer")


# ==== Dependencia para obtener el usuario actual a partir del token ====

def get_current_player(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Player:
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido.",
            )
        player_id = int(sub)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
        )

    player = db.query(models.Player).filter(models.Player.id_players == player_id).first()
    if player is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado.",
        )
    return player


@app.get("/whoami", response_model=schemas.PlayerOut)
def whoami(current_player: models.Player = Depends(get_current_player)):
    """
    Devuelve la información básica del jugador actual, según el JWT.
    """
    return current_player
