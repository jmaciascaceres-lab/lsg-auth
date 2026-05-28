# Manual de Usuario - LSG-Auth
## Servicio de Autenticación LifeSync-Games

**URL del servicio:** https://lsg.diinf.usach.cl/lsg-auth/docs  
**Versión:** 1.2.0.3 | **Proyecto:** LifeSync-Games - InTeractiOn Lab, USACH

---

## ¿Qué es LSG-Auth?

LSG-Auth es el servicio que gestiona la identidad de todos los usuarios del ecosistema LifeSync-Games. Antes de usar cualquier endpoint de la API principal (LSG-Core-API), necesitas obtener un **token de acceso (JWT)** desde este servicio.

---

## 1. Conceptos clave

### ¿Qué es un token JWT?
Un token JWT (JSON Web Token) es una credencial temporal que identifica quién eres y qué puedes hacer. Tiene la forma `eyJhbGci...` y expira en **120 minutos**. Debes renovarlo antes de que expire.

### Roles del sistema
Cada usuario tiene uno o más roles que determinan a qué puede acceder:

| Rol | Qué puede hacer |
|-----|-----------------|
| `player` | Ver y usar únicamente sus propios datos |
| `teacher` | Leer datos de todos los jugadores y analíticas |
| `researcher` | Todo lo de teacher + ajustar puntos y exportar datos FONDECYT |
| `admin` | Acceso completo al sistema |
| `developer` | Desarrollar mods para el sistema |

---

## 2. Cómo empezar - flujo básico

```
1. Ir a: https://lsg.diinf.usach.cl/lsg-auth/docs
2. Hacer login → POST /login
3. Copiar el access_token recibido
4. Ir a: https://lsg.diinf.usach.cl/lsg-core-api/docs
5. Botón "Authorize" → pegar Bearer <token>
6. Usar los endpoints
```

---

## 3. Endpoints detallados

---

### 3.1 GET /health - Verificar que el servicio está funcionando

**¿Para qué sirve?**  
Confirmar que el servicio LSG-Auth y su conexión a la base de datos están operativos. No requiere autenticación.

**Roles requeridos:** ninguno

```bash
curl -X GET 'https://lsg.diinf.usach.cl/lsg-auth/health'
```

**Respuesta exitosa (200):**
```json
{"status": "ok", "db": "ok"}
```

---

### 3.2 POST /login - Iniciar sesión y obtener token

**¿Para qué sirve?** Autenticarte con tu email y contraseña para obtener el token JWT.

**Roles requeridos:** ninguno

**Importante:** En el Swagger el campo se llama `username`, pero debes ingresar tu **email**.

```bash
curl -X POST 'https://lsg.diinf.usach.cl/lsg-auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=tu.email@usach.cl&password=tu_contraseña'
```

**Respuesta exitosa (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

| Código | Causa | Solución |
|--------|-------|----------|
| 401 | Email o contraseña incorrectos | Verificar credenciales |
| 422 | Formato inválido | Enviar como formulario, no JSON |

Usa el token como: `Authorization: Bearer eyJhbGci...`

---

### 3.3 GET /whoami - Ver mi información actual

**¿Para qué sirve?** Verificar que tu token es válido y ver tu perfil con roles activos.

**Roles requeridos:** cualquier rol autenticado

```bash
curl -X GET 'https://lsg.diinf.usach.cl/lsg-auth/whoami' \
  -H 'Authorization: Bearer <tu_token>'
```

**Respuesta exitosa (200):**
```json
{
  "id_players": 46,
  "name": "jmacias",
  "email": "joaquin.macias@usach.cl",
  "age": 30,
  "roles": ["admin", "player"]
}
```

---

### 3.4 GET /token/remaining - ¿Cuánto tiempo le queda a mi token?

**¿Para qué sirve?** Consultar cuántos segundos le quedan al token antes de expirar.

**Roles requeridos:** cualquier rol autenticado

```bash
curl -X GET 'https://lsg.diinf.usach.cl/lsg-auth/token/remaining' \
  -H 'Authorization: Bearer <tu_token>'
```

**Respuesta exitosa (200):**
```json
{
  "expires_in_seconds": 6843,
  "expires_at": "2026-05-07T12:23:41+00:00",
  "issued_at": "2026-05-07T10:23:41+00:00"
}
```

**Consejo:** Si `expires_in_seconds` < 300, renueva el token con `POST /token/refresh` o `POST /login`.

---

### 3.5 POST /token/refresh - Renovar token sin hacer login

**¿Para qué sirve?** Generar un nuevo token usando el token actual vigente, sin ingresar credenciales. Los roles se actualizan automáticamente desde la BD.

**Roles requeridos:** cualquier rol autenticado (token vigente, no expirado)

```bash
curl -X POST 'https://lsg.diinf.usach.cl/lsg-auth/token/refresh' \
  -H 'Authorization: Bearer <token_vigente>' \
  -d ''
```

**Respuesta exitosa (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

| Código | Causa | Solución |
|--------|-------|----------|
| 401 | Token expirado o inválido | Usar `POST /login` para obtener token nuevo |

> **Útil para:** scripts o mods de videojuego que necesitan mantener sesión activa durante más de 120 minutos sin guardar contraseña en el código.

---

### 3.6 POST /players - Crear nuevo usuario (solo admin)

**¿Para qué sirve?** Crear una nueva cuenta de usuario. Solo administradores pueden hacerlo desde la API. El primer admin debe crearse desde la consola del servidor.

**Roles requeridos:** `admin`

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `name` | string | Sí | Nombre completo |
| `email` | string | Sí | Email único (username para login) |
| `password` | string | Sí | Contraseña en texto plano (se hashea con bcrypt) |
| `age` | integer | No | Edad del participante |
| `role` | string | No | Rol inicial: `player`, `teacher`, `researcher`, `admin`. Default: `player` |

```bash
curl -X POST 'https://lsg.diinf.usach.cl/lsg-auth/players' \
  -H 'Authorization: Bearer <token_admin>' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "María González",
    "email": "maria.gonzalez@usach.cl",
    "password": "contraseña_segura_123",
    "age": 22,
    "role": "player"
  }'
```

**Respuesta exitosa (201):**
```json
{
  "id_players": 57,
  "name": "María González",
  "email": "maria.gonzalez@usach.cl",
  "age": 22,
  "roles": ["player"]
}
```

| Código | Causa | Solución |
|--------|-------|----------|
| 400 | Email ya registrado | Usar otro email |
| 403 | Token sin rol admin | Necesitas token de administrador |

---

### 3.7 PATCH /admin/players/{id}/roles - Asignar o revocar un rol

**¿Para qué sirve?** Cambiar los roles de un jugador: agregar (`grant`) o quitar (`revoke`). Un jugador puede tener múltiples roles activos.

**Roles requeridos:** `admin`

| Campo | Valores | Descripción |
|-------|---------|-------------|
| `role` | `player`, `teacher`, `researcher`, `admin`, `developer` | Rol a modificar |
| `action` | `grant`, `revoke` | `grant` agrega, `revoke` quita |

```bash
# Asignar rol researcher al jugador 57
curl -X PATCH 'https://lsg.diinf.usach.cl/lsg-auth/admin/players/57/roles' \
  -H 'Authorization: Bearer <token_admin>' \
  -H 'Content-Type: application/json' \
  -d '{"role": "teacher", "action": "grant"}'
```

**Respuesta exitosa (200):**
```json
{"status": "ok", "player_id": 57, "role": "teacher", "action": "grant"}
```

**Notas:**
- `grant` es idempotente: si el rol ya existe, no lo duplica.
- `revoke` no borra el historial; marca el rol con timestamp de revocación.

---

### 3.8 GET /admin/players/{id}/roles - Ver historial de roles

**¿Para qué sirve?** Consultar todos los roles (activos e históricos) de un jugador.

**Roles requeridos:** `admin`

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `{id}` (ruta) | integer | `id_players` del jugador |
| `include_revoked` (query) | boolean | `true` (default): todos. `false`: solo activos |

```bash
# Ver solo roles activos del jugador 57
curl -X GET 'https://lsg.diinf.usach.cl/lsg-auth/admin/players/57/roles?include_revoked=false' \
  -H 'Authorization: Bearer <token_admin>'
```

**Respuesta exitosa (200):**
```json
[
  {
    "id_player_role": 15,
    "role": "teacher",
    "assigned_at": "2026-05-07T10:52:46",
    "assigned_by": 46,
    "revoked_at": null,
    "is_active": true
  },
  {
    "id_player_role": 14,
    "role": "player",
    "assigned_at": "2026-05-07T10:48:52",
    "assigned_by": 46,
    "revoked_at": null,
    "is_active": true
  }
]
```

---

## 4. Preguntas frecuentes

**P: Mi token expiró, ¿qué hago?**  
R: Usa `POST /token/refresh` si el token aún no expiró, o `POST /login` si ya expiró.

**P: ¿Puedo tener varios roles al mismo tiempo?**  
R: Sí. Un usuario puede tener `player` y `researcher` simultáneamente.

**P: ¿Cómo sé cuál es mi `id_players`?**  
R: Usa `GET /whoami` y verás el campo `id_players` en la respuesta.

**P: ¿Cómo veo los roles actuales de un jugador?**  
R: Usa `GET /admin/players/{id}/roles?include_revoked=false` (solo admin).

**P: ¿Por qué mi token no funciona en lsg-core-api?**  
R: Verifica el formato exacto `Bearer <token>` en el header `Authorization`, y que el token no expiró (`GET /token/remaining`).

---

## 5. Historial de versiones

### v1.1.1 (2026-05-08)
- **Corrección crítica:** se agrega la clase `RoleAssignRequest` a `schemas.py`, que faltaba y impedía que el servicio iniciara (`AttributeError` en startup de uvicorn).  
  Campos del esquema: `role: str` y `action: Literal["grant", "revoke"]`.
- **Migración Pydantic v2:** se corrigen dos deprecaciones que generaban `UserWarning` al iniciar el contenedor:
  - `orm_mode = True` → `model_config = {"from_attributes": True}` en `PlayerOut`.
  - `min_anystr_length` → `str_min_length` en `PasswordChangeRequest`.
- El endpoint `PATCH /admin/players/{id}/roles` (sección 3.7) ahora valida el campo `action` automáticamente con un error `422` descriptivo cuando el valor no es `grant` ni `revoke`.