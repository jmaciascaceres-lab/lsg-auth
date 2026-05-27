import os
from datetime import timedelta, datetime
import time

from fastapi import FastAPI, Depends, HTTPException, Request, Security
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import (
    verify_password,
    hash_password,
    create_access_token,
    decode_access_token,
    get_token_remaining,
)
from app.db import get_db

# Configuración
AUTH_DISABLED = os.getenv("AUTH_DISABLED", "false").lower() == "true"
ROOT_PATH     = os.getenv("LSG_AUTH_ROOT_PATH", "")

AUTH_DOCS_DESCRIPTION = """
## LSG-Auth - Servicio de Autenticación

Gestiona jugadores, roles y tokens JWT para el ecosistema LifeSync-Games.

**Flujo básico:**
1. `POST /login` con tu email y contraseña → obtén `access_token`
2. Úsalo en LSG-Core-API: botón **Authorize** → `Bearer <token>`
3. El token expira en **120 minutos**. Renuévalo con `POST /token/refresh`.

**Roles:** `player` | `teacher` | `researcher` | `admin` | `developer`
"""

app = FastAPI(
    title       = "LSG-Auth",
    version     = "1.2.0.1",
    root_path   = ROOT_PATH,
    description = AUTH_DOCS_DESCRIPTION,
)

_bearer_scheme = HTTPBearer(auto_error=False)

# Helpers internos

def require_roles(allowed_roles: list):
    """Dependencia: valida que el token tenga al menos uno de los roles indicados."""
    from fastapi import Security
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

    bearer = HTTPBearer(auto_error=False)

    def _check(
        credentials: HTTPAuthorizationCredentials = Security(bearer),
        db: Session = Depends(get_db),
    ):
        if AUTH_DISABLED:
            # Modo desarrollo sin BD de auth
            admin = models.Player(id_players=0, name="dev_admin", email="admin@dev")
            admin._roles = [models.PlayerRole(role="admin")]
            return admin

        if not credentials:
            raise HTTPException(status_code=401, detail="Token requerido.")

        try:
            payload = decode_access_token(credentials.credentials)
        except Exception:
            raise HTTPException(status_code=401, detail="Token inválido o expirado.")

        player_id = int(payload.get("sub", 0))
        player = db.query(models.Player).filter(
            models.Player.id_players == player_id
        ).first()
        if not player:
            raise HTTPException(status_code=401, detail="Usuario no encontrado.")

        active_roles = player.roles   # propiedad del modelo que lee player_roles
        if not any(r in allowed_roles for r in active_roles):
            raise HTTPException(
                status_code=403,
                detail=f"Se requiere uno de estos roles: {allowed_roles}",
            )
        return player

    return _check


def _get_current_player(
    credentials=None,
    db: Session = Depends(get_db),
):
    """Dependencia: cualquier rol autenticado."""
    from fastapi import Security
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    bearer = HTTPBearer()
    # (implementación simplificada — en producción usar la misma lógica de require_roles)
    return None   # placeholder; la implementación real está en el repo


# GET /health

@app.get("/health", tags=["health"])
def health(db: Session = Depends(get_db)):
    """
    # GET /health

    Healthcheck del servicio y conexión a BD.
    """
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB error: {e}")


# POST /login

@app.post("/login", tags=["auth"])
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db:   Session = Depends(get_db),
):
    """
    # POST /login

    Inicio de sesión. El campo `username` debe contener el **email** del usuario.

    Retorna el JWT (válido **120 minutos**) junto con el perfil básico del jugador,
    eliminando la necesidad de un `GET /whoami` adicional tras el login.

    **Respuesta:**
    ```json
    {
      "access_token": "eyJ...",
      "token_type": "bearer",
      "expires_in_seconds": 7200,
      "expires_at": "2026-05-20T14:30:00+00:00",
      "player": {
        "id_players": 50,
        "name": "irojas",
        "email": "isidora.rojas.a@usach.cl",
        "age": 30,
        "roles": ["developer", "player"]
      }
    }
    ```

    **Roles disponibles:** "admin", "researcher", "teacher", "player", "developer"
    """
    import time as _time
    from datetime import timezone as _tz

    player = db.query(models.Player).filter(
        models.Player.email == form.username
    ).first()

    if not player or not verify_password(form.password, player.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas.")

    # Verificar si es cuenta temporal expirada
    if player.is_temp_expired:
        raise HTTPException(
            status_code=401,
            detail={
                "code":    "TEMP_ACCOUNT_EXPIRED",
                "message": "Tu cuenta temporal ha expirado. Contacta al administrador.",
                "expired_at": str(player.temp_expires_at),
            },
        )

    active_roles = player.roles
    token = create_access_token({
        "sub":       str(player.id_players),
        "player_id": player.id_players,
        "email":     player.email,
        "roles":     active_roles,
        "type":      "user",
    })

    # Calcular expires_at desde el token generado
    decoded = decode_access_token(token)
    exp_ts  = decoded.get("exp", 0)
    now_ts  = int(_time.time())

    return {
        "access_token":     token,
        "token_type":       "bearer",
        "expires_in_seconds": max(0, exp_ts - now_ts),
        "expires_at":       datetime.fromtimestamp(exp_ts, tz=_tz.utc).isoformat(),
        "player": {
            "id_players": player.id_players,
            "name":       player.name,
            "email":      player.email,
            "age":        player.age,
            "roles":      active_roles,
        },
    }


# GET /whoami

@app.get("/whoami", tags=["auth"])
def whoami(
    current: models.Player = Depends(require_roles(
        ["admin", "researcher", "teacher", "player", "developer"]
    )),
):
    """
    # GET /whoami

    Perfil del usuario autenticado, incluyendo roles activos.
    
    **Roles disponibles:** "admin", "researcher", "teacher", "player", "developer"
    """
    return {
        "id_players": current.id_players,
        "name":       current.name,
        "email":      current.email,
        "age":        current.age,
        "roles":      current.roles,
    }


# GET /token/remaining

@app.get("/token/remaining", tags=["auth"])
def token_remaining_endpoint(
    credentials: HTTPAuthorizationCredentials = Security(_bearer_scheme),
):
    """
    # GET /token/remaining

    Devuelve cuántos segundos le quedan al token activo.

    No requiere el flujo completo de roles — solo decodifica el JWT del header
    para leer el claim `exp` y calcular la diferencia con UTC ahora.

    Si `expires_in_seconds` llega a 0, el token ya expiró → usar `POST /login`.

    **Roles disponibles:** "admin", "researcher", "teacher", "player", "developer"
    """
    import time as _time

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Header Authorization: Bearer <token> requerido.",
        )
    raw_token = credentials.credentials  # ya viene sin "Bearer "

    try:
        payload = decode_access_token(raw_token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado. Usa POST /login para obtener uno nuevo.",
        )

    exp_ts = payload.get("exp")
    if not exp_ts:
        raise HTTPException(status_code=400, detail="El token no contiene campo 'exp'.")

    now_ts          = int(_time.time())
    remaining       = max(0, int(exp_ts) - now_ts)
    expires_at_dt   = datetime.utcfromtimestamp(exp_ts).strftime("%Y-%m-%dT%H:%M:%SZ")
    issued_at       = payload.get("iat")
    issued_at_str   = (datetime.utcfromtimestamp(issued_at).strftime("%Y-%m-%dT%H:%M:%SZ")
                       if issued_at else None)

    return {
        "expires_in_seconds": remaining,
        "expires_at":         expires_at_dt,
        "issued_at":          issued_at_str,
        "player_id":          payload.get("player_id"),
        "roles":              payload.get("roles", []),
    }


# POST /token/refresh

@app.post("/token/refresh", response_model=schemas.Token, tags=["auth"])
def refresh_token(
    current: models.Player = Depends(require_roles(
        ["admin", "researcher", "teacher", "player", "developer"]
    )),
):
    """
    # POST /token/refresh

    Renueva el token JWT sin necesidad de hacer login nuevamente.
    Los roles se actualizan desde la BD en el nuevo token.

    Útil para scripts y mods que necesitan sesión activa prolongada.

    **Roles disponibles:** "admin", "researcher", "teacher", "player", "developer"
    """
    active_roles = current.roles
    new_token = create_access_token({
        "sub":       str(current.id_players),
        "player_id": current.id_players,
        "email":     current.email,
        "roles":     active_roles,
        "type":      "user",
    })
    return {
        "access_token": new_token,
        "token_type":   "bearer",
        "player": {
            "id_players": current.id_players,
            "name":       current.name,
            "email":      current.email,
            "age":        current.age,
            "roles":      current.roles,
        },
    }


# POST /players

@app.post("/players", status_code=201, tags=["admin"])
def create_player(
    payload:       schemas.PlayerCreate,
    db:            Session = Depends(get_db),
    current_admin: models.Player = Depends(require_roles(["admin"])),
):
    """
    # POST /players

    Crea un nuevo jugador/participante LSG. 

    El primer usuario admin debe crearse desde el CLI del contenedor:
    ```
    docker compose exec app python -m app.cli_create_user --email admin@lsg.cl --role admin
    ```

    **Roles disponibles:** "admin"
    """
    existing = db.query(models.Player).filter(
        models.Player.email == payload.email
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email ya registrado.")

    valid_roles = {"player", "teacher", "researcher", "admin", "developer"}
    role = payload.role or "player"
    if role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Rol inválido. Opciones: {valid_roles}",
        )

    new_player = models.Player(
        name          = payload.name,
        email         = payload.email,
        password_hash = hash_password(payload.password),
        age           = payload.age,
    )
    db.add(new_player)
    db.flush()

    db.add(models.PlayerRole(
        id_players  = new_player.id_players,
        role        = role,
        assigned_by = current_admin.id_players,
    ))
    db.commit()
    db.refresh(new_player)

    return {
        "id_players": new_player.id_players,
        "name":       new_player.name,
        "email":      new_player.email,
        "age":        new_player.age,
        "roles":      new_player.roles,
    }


# PATCH /admin/players/{player_id}/roles

@app.patch("/admin/players/{player_id}/roles", tags=["admin"],
           summary="Asignar o revocar rol a un jugador ")
def manage_player_role(
    player_id:     int,
    body:          schemas.RoleAssignRequest,
    db:            Session = Depends(get_db),
    current_admin: models.Player = Depends(require_roles(["admin"])),
):
    """
    # PATCH /admin/players/{player_id}/roles

    Asigna (`grant`) o revoca (`revoke`) un rol a un jugador.

    - **grant**: idempotente — si el rol ya existe activo, no lo duplica.
    - **revoke**: marca `revoked_at = NOW()`, no borra el historial.

    Ejemplo:
    ```json
    { "role": "researcher", "action": "grant" }
    ```

    **Roles disponibles:** "admin"
    """
    target = db.query(models.Player).filter(
        models.Player.id_players == player_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Jugador no encontrado.")

    valid_roles = {"player", "teacher", "researcher", "admin", "developer"}
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Opciones: {valid_roles}")

    if body.action == "grant":
        existing = db.query(models.PlayerRole).filter(
            models.PlayerRole.id_players == player_id,
            models.PlayerRole.role       == body.role,
            models.PlayerRole.revoked_at.is_(None),
        ).first()
        if not existing:
            db.add(models.PlayerRole(
                id_players  = player_id,
                role        = body.role,
                assigned_by = current_admin.id_players,
            ))
            db.commit()

    elif body.action == "revoke":
        from sqlalchemy import func
        db.query(models.PlayerRole).filter(
            models.PlayerRole.id_players == player_id,
            models.PlayerRole.role       == body.role,
            models.PlayerRole.revoked_at.is_(None),
        ).update({"revoked_at": func.now()})
        db.commit()
    else:
        raise HTTPException(status_code=400, detail="action debe ser 'grant' o 'revoke'.")

    return {"status": "ok", "player_id": player_id, "role": body.role, "action": body.action}


# GET /admin/players/{player_id}/roles

@app.get("/admin/players/{player_id}/roles", tags=["admin"],
         summary="Historial de roles de un jugador")
def get_player_roles(
    player_id:       int,
    include_revoked: bool = True,
    db:              Session = Depends(get_db),
    _:               models.Player = Depends(require_roles(["admin"])),
):
    """
    # GET /admin/players/{player_id}/roles

    Devuelve todos los roles (activos e históricos) de un jugador.

    - `include_revoked=true` (default): activos + revocados.
    - `include_revoked=false`: solo roles activos (`revoked_at IS NULL`).

    **Roles disponibles:** "admin"
    """
    target = db.query(models.Player).filter(
        models.Player.id_players == player_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Jugador no encontrado.")

    roles = target._roles
    if not include_revoked:
        roles = [r for r in roles if r.revoked_at is None]

    return [
        {
            "id_player_role": pr.id_player_role,
            "role":           pr.role,
            "assigned_at":    pr.assigned_at,
            "assigned_by":    pr.assigned_by,
            "revoked_at":     pr.revoked_at,
            "is_active":      pr.revoked_at is None,
        }
        for pr in sorted(roles, key=lambda r: r.assigned_at or datetime.min, reverse=True)
    ]


# POST /admin/players/batch-temp — Cuentas temporales para developers

@app.post(
    "/admin/players/batch-temp",
    tags=["admin"],
    summary="Crear lote de cuentas temporales",
    status_code=201,
)
def create_batch_temp_players(
    body:          schemas.BatchTempPlayersRequest,
    db:            Session = Depends(get_db),
    current_admin: models.Player = Depends(require_roles(["admin"])),
):
    """
    # POST /admin/players/batch-temp

    Crea un lote de cuentas temporales para que developers puedan probar mods.

    Cada cuenta recibe:
    - Un **email** único autogenerado: `{prefix}_{6chars}@lsg.temp`
    - Una **contraseña** aleatoria de 6 caracteres alfanuméricos
    - Un **rol** definido en el request (default: `player`)
    - Una **fecha de expiración**: después de esa fecha el login es bloqueado

    **Guarda las contraseñas en el momento de la respuesta.**
    No se pueden recuperar después (solo se almacena el hash bcrypt).

    **Límite:** 1 a 50 cuentas por llamada. Días de activación: 1 a 90.

    **cURL:**
    ```bash
    curl -X POST 'https://lsg.diinf.usach.cl/lsg-auth/admin/players/batch-temp' \
      -H 'Authorization: Bearer <TOKEN_ADMIN>' \
      -H 'Content-Type: application/json' \
      -d '{
        "count": 5,
        "days_active": 14,
        "role": "developer",
        "name_prefix": "test"
      }'
    ```

    **Roles disponibles:** "admin"
    """
    import random
    import string
    from datetime import timezone

    # Validaciones
    if not (1 <= body.count <= 50):
        raise HTTPException(status_code=400, detail="count debe estar entre 1 y 50.")
    if not (1 <= body.days_active <= 90):
        raise HTTPException(status_code=400, detail="days_active debe estar entre 1 y 90.")

    valid_roles = {"player", "teacher", "researcher", "admin", "developer"}
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Opciones: {valid_roles}")

    chars     = string.ascii_lowercase + string.digits
    expires_dt = datetime.utcnow() + timedelta(days=body.days_active)
    expires_str = expires_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    created = []

    for _ in range(body.count):
        # Generar sufijo único de 6 caracteres
        suffix    = "".join(random.choices(chars, k=6))
        temp_email = f"{body.name_prefix}_{suffix}@lsg.temp"
        temp_pass  = "".join(random.choices(chars, k=6))

        # Verificar unicidad del email (reintento si ya existe)
        attempts = 0
        while db.query(models.Player).filter(
            models.Player.email == temp_email
        ).first() and attempts < 10:
            suffix     = "".join(random.choices(chars, k=6))
            temp_email = f"{body.name_prefix}_{suffix}@lsg.temp"
            attempts  += 1

        new_player = models.Player(
            name          = f"{body.name_prefix}_{suffix}",
            email         = temp_email,
            password_hash = hash_password(temp_pass),
            temp_expires_at = expires_dt,
        )
        db.add(new_player)
        db.flush()

        db.add(models.PlayerRole(
            id_players  = new_player.id_players,
            role        = body.role,
            assigned_by = current_admin.id_players,
        ))

        created.append({
            "id_players":    new_player.id_players,
            "email":         temp_email,
            "temp_password": temp_pass,   # ← solo visible al crear
            "role":          body.role,
            "expires_at":    expires_str,
        })

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creando cuentas: {e}")

    return {
        "status":      "ok",
        "count":       len(created),
        "expires_at":  expires_str,
        "role":        body.role,
        "accounts":    created,
        "warning":     "Guarda las contraseñas ahora. No se podrán recuperar.",
    }


# PATCH /admin/players/{player_id}/password

@app.patch(
    "/admin/players/{player_id}/password",
    tags=["admin"],
    summary="Cambiar contraseña de un jugador",
)
def change_player_password(
    player_id:     int,
    body:          schemas.PasswordChangeRequest,
    db:            Session = Depends(get_db),
    current_admin: models.Player = Depends(require_roles(["admin"])),
):
    """
    # PATCH /admin/players/{player_id}/password

    Cambia la contraseña de cualquier jugador del sistema.

    La nueva contraseña se hashea con **bcrypt** antes de almacenarse.
    Nunca se guarda en texto plano.

    **cURL:**
    ```bash
    curl -X PATCH 'https://lsg.diinf.usach.cl/lsg-auth/admin/players/57/password' \\
      -H 'Authorization: Bearer <TOKEN_ADMIN>' \\
      -H 'Content-Type: application/json' \\
      -d '{"new_password": "nueva_contraseña_segura"}'
    ```

    **Respuesta exitosa (200):**
    ```json
    {
      "status": "ok",
      "player_id": 57,
      "message": "Contraseña actualizada correctamente."
    }
    ```

    **Roles disponibles:** "admin"
    """
    target = db.query(models.Player).filter(
        models.Player.id_players == player_id
    ).first()

    if not target:
        raise HTTPException(
            status_code=404,
            detail=f"Jugador {player_id} no encontrado.",
        )

    new_hash = hash_password(body.new_password)

    try:
        db.query(models.Player).filter(
            models.Player.id_players == player_id
        ).update({"password_hash": new_hash})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando contraseña: {e}",
        )

    return {
        "status":    "ok",
        "player_id": player_id,
        "message":   "Contraseña actualizada correctamente.",
    }