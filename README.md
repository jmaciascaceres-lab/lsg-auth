# LSG-Auth — Servicio de Autenticación LifeSync-Games

Servicio de autenticación JWT para el ecosistema LifeSync-Games (LSG), basado en **FastAPI**, **MySQL** y **JWT**.

**Versión:** 1.1.0 | **Swagger:** https://lsg.diinf.usach.cl/lsg-auth/docs

Provee:
- Gestión de jugadores con contraseña hasheada con **bcrypt**.
- Inicio de sesión con token JWT (claim `roles` como lista).
- Sistema de **roles múltiples** por jugador (`player_roles`).
- Endpoint `GET /token/remaining` para consultar segundos restantes del token.
- Endpoint `PATCH /admin/players/{id}/roles` para asignar/revocar roles (solo admin).
- Healthcheck de la API y de la conexión a la base de datos.

---

## Estructura del proyecto

```text
lsg-auth/
│
├── app/
│   ├── tools/
│   │   └── generate_jwt_secret.py   # genera AUTH_JWT_SECRET (ignorado por git)
│   ├── __init__.py
│   ├── auth.py                      # bcrypt + JWT + get_token_remaining()
│   ├── cli_create_user.py           # CLI para bootstrap de usuarios (primer admin)
│   ├── db.py                        # conexión SQLAlchemy a MySQL
│   ├── main.py                      # FastAPI: endpoints + require_roles()
│   ├── models.py                    # ORM: Player, PlayerRole
│   └── schemas.py                   # Pydantic v2: PlayerCreate/Out, Token, RoleAssign
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── README.md
└── requirements.txt
```

---

## Endpoints

| Método | Ruta | Rol requerido | Descripción |
|--------|------|---------------|-------------|
| `GET`  | `/health` | — | Healthcheck + SELECT 1 en BD |
| `POST` | `/login`  | — | Login OAuth2 → JWT (120 min) |
| `GET`  | `/whoami` | cualquiera | Perfil + roles del token activo |
| `GET`  | `/token/remaining` | cualquiera | Segundos restantes del JWT |
| `POST` | `/players` | `admin` | Crear jugador con rol inicial |
| `PATCH`| `/admin/players/{id}/roles` | `admin` | Asignar (`grant`) o revocar (`revoke`) rol |

---

## Sistema de roles

Un jugador puede tener **N roles activos simultáneamente** (tabla `player_roles`).  
El JWT emite el claim `"roles": ["player", "researcher"]` (lista, no string singular).

| Rol | Descripción |
|-----|-------------|
| `player` | Visualización y uso de servicios propios |
| `teacher` | Lectura de todos los jugadores y analíticas |
| `researcher` | Todo lo de teacher + edición, exportación e IC² ajeno |
| `admin` | Acceso completo incluyendo configuración del sistema |

---

## Esquema de tablas relevantes

```sql
-- Tabla players (v1.1: sin columna 'role')
CREATE TABLE players (
  id_players    INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(50) NOT NULL,
  password_hash CHAR(95) DEFAULT NULL,
  email         VARCHAR(128) NOT NULL UNIQUE,
  age           INT,
  external_type VARCHAR(16),
  external_id   VARCHAR(128),
  updated_at    TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla player_roles (multi-rol, historial con revocación)
CREATE TABLE player_roles (
  id_player_role INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_players     INT NOT NULL,
  role           VARCHAR(32) NOT NULL,
  assigned_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  assigned_by    INT NULL,           -- id_players del admin asignador
  revoked_at     TIMESTAMP NULL,     -- NULL = rol activo
  CONSTRAINT chk_pr_role CHECK (role IN ('player','researcher','admin','teacher')),
  FOREIGN KEY (id_players) REFERENCES players(id_players)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## Variables de entorno

```env
# ── Base de datos ──────────────────────────────────────────────────────────────
# DB_HOST y DB_PORT son inyectados por docker-compose (lsg_db:3306)
DB_NAME=db_lsg
DB_USER=lsg_user
DB_PASSWORD=PASSWORD

# ── JWT ────────────────────────────────────────────────────────────────────────
# Debe coincidir exactamente con lsg-core-api-prod
AUTH_JWT_SECRET=VALOR_LARGO_Y_ALEATORIO_GENERADO
AUTH_JWT_ALGORITHM=HS256
AUTH_JWT_ISSUER=lsg-auth
AUTH_JWT_AUDIENCE=lsg-core-api
JWT_EXPIRE_MINUTES=120

# ── Guards ─────────────────────────────────────────────────────────────────────
# false en producción SIEMPRE
AUTH_DISABLED=false
```

### Generar AUTH_JWT_SECRET

```bash
python -m app.tools.generate_jwt_secret
# Copiar el valor generado y pegarlo en .env de AMBOS repos (auth y core-api)
```

---

## Despliegue en producción (DIINF-USACH)

### Prerequisito: red compartida con lsg-core-api-prod

```bash
# Crear solo una vez por VM (si no existe)
docker network create lsg_shared
```

### Levantar el servicio

```bash
cp .env.example .env
# Editar .env con los valores reales
docker compose up -d --build
docker ps
docker logs -n 100 lsg_auth
```

### Crear el primer admin (bootstrap)

La creación de usuarios desde el endpoint `/players` requiere un token admin.  
Para el bootstrap inicial usar el CLI directamente en el contenedor:

```bash
docker compose exec app \
  python -m app.cli_create_user \
    --name "Admin LSG" \
    --email admin@lsg.cl \
    --password "contraseña_segura" \
    --role admin
```

### Verificar

```bash
# Swagger
open https://lsg.diinf.usach.cl/lsg-auth/docs

# Health
curl https://lsg.diinf.usach.cl/lsg-auth/health
```

---

## Desarrollo local (sin Docker)

```bash
cd lsg-auth

# Crear y activar entorno virtual
python -m venv .venv
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# Linux/macOS
source .venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env: añadir DB_HOST=127.0.0.1, DB_PORT=3306 para dev local
# (no están en .env.example porque en producción los inyecta docker-compose)

# Levantar API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Swagger: http://localhost:8000/docs
```

> Para dev local añadir al `.env`:
> ```
> DB_HOST=127.0.0.1
> DB_PORT=3306       # o el puerto del túnel SSH si es BD remota
> ```

---

## Flujo de uso

```
1. Login:
   POST /login  {username: email, password: "..."}
   → {"access_token": "eyJ...", "token_type": "bearer"}

   Payload del JWT:
   {
     "sub": "26",
     "player_id": 26,
     "email": "joaquin.macias@usach.cl",
     "roles": ["admin", "researcher"],   ← lista (v1.1+)
     "type": "user",
     "exp": ...,
     "iss": "lsg-auth",
     "aud": "lsg-core-api"
   }

2. Consultar tiempo restante:
   GET /token/remaining  Authorization: Bearer <token>
   → {"expires_in_seconds": 487, "expires_at": "2026-05-06T15:23:41Z"}

3. Usar token en lsg-core-api-prod:
   Authorization: Bearer <token>  (válido 120 minutos)

4. Gestión de roles (admin):
   PATCH /admin/players/46/roles
   Body: {"role": "researcher", "action": "grant"}
   → {"status": "ok", "player_id": 46, "role": "researcher", "action": "grant"}
```

---

## Changelog

### v1.1.0 (2026-05)
- Sistema de roles multi-rol (`player_roles`): un jugador puede tener N roles activos.
- JWT emite `"roles": [...]` (lista) en lugar de `"role": "..."` (string).  
  Compatibilidad backward: `security.py` de `lsg-core-api-prod` acepta ambos formatos.
- `JWT_EXPIRE_MINUTES` aumentado de 10 a **120 minutos**.
- Nuevo endpoint `GET /token/remaining`.
- Nuevo endpoint `PATCH /admin/players/{id}/roles` (grant/revoke).
- Creación de usuarios (`POST /players`) restringida a rol `admin`.
- `models.py`: eliminada columna `role` de `Player`; agregado modelo `PlayerRole`.
- `schemas.py`: migración a Pydantic v2 (`ConfigDict`, `field_validator`).
- `cli_create_user.py`: inserta en `player_roles` en lugar de `players.role`.

---

## Referencias

- González-Ibáñez R., Macías-Cáceres J., Villalta-Paucar M. (2025). *LifeSync-Games: Toward a Video Game Paradigm for Promoting Responsible Gaming and Human Development*. arXiv:2510.19691 [cs.HC]. DOI: https://arxiv.org/abs/2510.19691