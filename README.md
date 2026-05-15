# LSG-Auth - Servicio de Autenticación LifeSync-Games

Servicio de autenticación JWT para el ecosistema LifeSync-Games (LSG), basado en **FastAPI**, **MySQL** y **JWT**.

**Versión:** 1.2.0.1 | **Swagger:** https://lsg.diinf.usach.cl/lsg-auth/docs

Provee:
- Gestión de jugadores con contraseña hasheada con **bcrypt**.
- Inicio de sesión con token JWT (claim `roles` como lista).
- Sistema de **roles múltiples** por jugador (`player_roles`).
- Endpoint `GET /token/remaining` para consultar segundos restantes del token.
- Endpoints `PATCH` y `GET /admin/players/{id}/roles` para gestionar roles (solo admin).
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
| `GET`  | `/health` | - | Healthcheck + SELECT 1 en BD |
| `POST` | `/login`  | - | Login OAuth2 → JWT (120 min) |
| `GET`  | `/whoami` | cualquiera | Perfil + roles del token activo |
| `GET`  | `/token/remaining` | cualquiera | Segundos restantes del JWT activo |
| `POST` | `/token/refresh` | cualquiera | Renovar token sin re-login (roles actualizados) |
| `POST` | `/players` | `admin` | Crear jugador con rol inicial |
| `POST` | `/admin/players/batch-temp` | `admin` | Crear lote de cuentas temporales (1-50) |
| `PATCH`| `/admin/players/{id}/roles` | `admin` | Asignar (`grant`) o revocar (`revoke`) rol |
| `GET`  | `/admin/players/{id}/roles` | `admin` | Historial de roles (activos + revocados) |
| `PATCH`| `/admin/players/{id}/password` | `admin` | Cambiar contraseña de cualquier jugador |

> **Nota:** La creación del primer usuario admin debe hacerse desde el CLI del contenedor (ver sección [Bootstrap](#crear-el-primer-admin-bootstrap)). El endpoint `POST /players` requiere un token admin activo.

---

## Sistema de roles

Un jugador puede tener **N roles activos simultáneamente** (tabla `player_roles`).  
El JWT emite el claim `"roles": ["player", "researcher"]` (lista, no string singular).

| Rol | Descripción |
|-----|-------------|
| `player` | Visualización y uso de servicios propios únicamente |
| `teacher` | Lectura de todos los jugadores y analíticas |
| `researcher` | Todo lo de teacher + edición, exportación e IC² ajeno |
| `developer` | Integración de mods: crear juegos, mecánicas y vincularlas |
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
  updated_at      TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  temp_expires_at TIMESTAMP NULL DEFAULT NULL  -- NULL = permanente; fecha = cuenta temporal
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla player_roles (multi-rol, historial con revocación)
CREATE TABLE player_roles (
  id_player_role INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_players     INT NOT NULL,
  role           VARCHAR(32) NOT NULL,
  assigned_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  assigned_by    INT NULL,           -- id_players del admin asignador (NULL = CLI bootstrap)
  revoked_at     TIMESTAMP NULL,     -- NULL = rol activo; timestamp = rol revocado
  CONSTRAINT chk_pr_role CHECK (role IN ('player','researcher','admin','teacher','developer')),
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

La creación de usuarios desde el endpoint `POST /players` requiere un token admin.  
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
# Health
curl https://lsg.diinf.usach.cl/lsg-auth/health

# Swagger
https://lsg.diinf.usach.cl/lsg-auth/docs
```

---

## Desarrollo local (sin Docker)

```bash
cd lsg-auth

# Crear y activar entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
source .venv/bin/activate       # Linux/macOS

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Agregar al .env para dev local:
#   DB_HOST=127.0.0.1
#   DB_PORT=3306

# Levantar API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Swagger: http://localhost:8000/docs
```

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
   → {"expires_in_seconds": 6843, "expires_at": "2026-05-07T12:23:41Z"}

3. Usar token en lsg-core-api-prod:
   Authorization: Bearer <token>  (válido 120 minutos)

4. Gestión de roles (admin):
   # Asignar rol
   PATCH /admin/players/46/roles
   Body: {"role": "researcher", "action": "grant"}
   → {"status": "ok", "player_id": 46, "role": "researcher", "action": "grant"}

   # Ver historial de roles (activos e históricos)
   GET /admin/players/46/roles
   GET /admin/players/46/roles?include_revoked=false  ← solo activos

   # Revocar rol
   PATCH /admin/players/46/roles
   Body: {"role": "researcher", "action": "revoke"}
```

---

## Changelog

### v1.2.0.1 (2026-05-13)

- Roles expandidos a "player" y "developer" para que puedan usar la API.

### v1.2.0 (2026-05-13)

**Nuevos endpoints:**
- `POST /token/refresh` - Renueva el JWT sin re-login; actualiza roles desde la BD.
- `POST /admin/players/batch-temp` - Genera lote de cuentas temporales (1-50) con email `{prefix}_{6chars}@lsg.temp`, contraseña aleatoria de 6 chars y fecha de expiración configurable (1-90 días). Las contraseñas solo son visibles en la respuesta de creación.
- `PATCH /admin/players/{id}/password` - Cambio de contraseña de cualquier jugador por el admin. Hasheo bcrypt automático.

**Bugfixes y mejoras:**
- `GET /token/remaining` - Corregido: retornaba `-1` (placeholder). Ahora decodifica el JWT real del header y calcula `exp - now()` correctamente.
- `models.py` - Refactorización completa:
  - Eliminada columna `role` obsoleta de `Player` (la BD ya la había eliminado en PATCH-01).
  - Agregada columna `temp_expires_at` en `Player` para cuentas temporales.
  - Nuevo modelo `PlayerRole` con relación `_roles` hacia `Player`.
  - Nueva propiedad `Player.roles` (lista de roles activos, `revoked_at IS NULL`).
  - Nueva propiedad `Player.is_temp_expired` para validar expiración en `POST /login`.
  - `password_hash` corregido a `nullable=True` (la BD permite auth externa vía CHECK).
- `POST /login` - Agrega verificación: si la cuenta temporal expiró (`temp_expires_at < NOW()`), retorna 401 con `"code": "TEMP_ACCOUNT_EXPIRED"`.
- `schemas.py` - Nuevos schemas: `BatchTempPlayersRequest`, `TempPlayerOut`, `RoleAssignRequest`.
- Rol `developer` incorporado al CHECK de `player_roles` (PATCH-09).
- BD PATCH-09: columna `temp_expires_at` en `players`, vistas `v_temp_players_active` y `v_temp_players_expired`.

### v1.1.1 (2026-05-08)
- **Bugfix:** agregada clase `RoleAssignRequest` a `schemas.py` (faltaba; causaba `AttributeError` en startup de uvicorn e impedía levantar el servicio).
- **Pydantic v2:** reemplazado `orm_mode = True` por `model_config = {"from_attributes": True}` en `PlayerOut`.
- **Pydantic v2:** reemplazado `min_anystr_length` por `str_min_length` en `PasswordChangeRequest`.
- El campo `action` en `RoleAssignRequest` ahora usa `Literal["grant", "revoke"]`; la validación pasa a Pydantic (422 automático) en lugar del `HTTPException` manual previo.

### v1.1.0 (2026-05)
- Sistema de roles multi-rol (`player_roles`): un jugador puede tener N roles activos.
- JWT emite `"roles": [...]` (lista) en lugar de `"role": "..."` (string). Compatibilidad backward: `security.py` de `lsg-core-api-prod` acepta ambos formatos durante la transición.
- `JWT_EXPIRE_MINUTES` ajustado a **120 minutos** para sesiones de investigación extendidas.
- Nuevo endpoint `GET /token/remaining` - tiempo restante sin consultar la BD.
- Nuevo endpoint `PATCH /admin/players/{id}/roles` - asignar/revocar roles (grant/revoke).
- Nuevo endpoint `GET /admin/players/{id}/roles` - historial completo de roles con `include_revoked`.
- Endpoint `POST /players` restringido a rol `admin`. Bootstrap via CLI.
- `models.py`: eliminada columna `role` de `Player`; nuevo modelo `PlayerRole`.
- `schemas.py`: migración a Pydantic v2 (`ConfigDict`, `field_validator`).
- `cli_create_user.py`: inserta en `player_roles` en lugar de `players.role`.

---

## Referencias

- R. González-Ibáñez, J. I. Macías-Cáceres and M. V. Paucar, "LifeSync-Games: A Technical Note on a Novel Framework for Video Game Development," 2025 44th International Conference of the Chilean Computer Science Society (SCCC), Valparaiso, Chile, 2025, pp. 1-4, doi: 10.1109/SCCC67219.2025.11420722.
- González-Ibáñez R., Macías-Cáceres J., Villalta-Paucar M. (2025). *LifeSync-Games: Toward a Video Game Paradigm for Promoting Responsible Gaming and Human Development*. arXiv:2510.19691 [cs.HC]. DOI: https://arxiv.org/abs/2510.19691