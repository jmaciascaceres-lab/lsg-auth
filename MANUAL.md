# Manual de Usuario - LSG-Auth
## Servicio de Autenticación LifeSync-Games

**URL del servicio:** https://lsg.diinf.usach.cl/lsg-auth/docs  
**Versión:** 1.1.0 | **Proyecto:** LifeSync-Games - InTeractiOn Lab, USACH

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

**Ejemplo de uso (curl):**
```bash
curl -X GET 'https://lsg.diinf.usach.cl/lsg-auth/health'
```

**Respuesta exitosa (200):**
```json
{
  "status": "ok",
  "db": "ok"
}
```

**Si hay problemas (503):**
```json
{
  "detail": "DB error: ..."
}
```

---

### 3.2 POST /login - Iniciar sesión y obtener token

**¿Para qué sirve?**  
Autenticarte con tu email y contraseña para obtener el token JWT que usarás en todos los demás endpoints.

**Roles requeridos:** ninguno (es el punto de entrada)

**⚠️ Importante:** En el Swagger, el campo se llama `username` pero debes ingresar tu **email**.

**Parámetros (formulario):**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `username` | string | Tu email registrado en el sistema |
| `password` | string | Tu contraseña |

**Ejemplo con curl:**
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

**Errores comunes:**

| Código | Causa | Solución |
|--------|-------|----------|
| 401 | Email o contraseña incorrectos | Verificar credenciales |
| 422 | Formato inválido | Verificar que se envía como formulario, no JSON |

**¿Cómo usar el token?**  
Copia el valor de `access_token` y úsalo en cualquier request como:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

### 3.3 GET /whoami - Ver mi información actual

**¿Para qué sirve?**  
Verificar que tu token es válido y ver tu perfil completo incluyendo los roles activos.

**Roles requeridos:** cualquier rol autenticado

**Ejemplo con curl:**
```bash
curl -X GET 'https://lsg.diinf.usach.cl/lsg-auth/whoami' \
  -H 'Authorization: Bearer <tu_token>'
```

**Respuesta exitosa (200):**
```json
{
  "id_players": 26,
  "name": "Joaquín Macías",
  "email": "joaquin.macias@usach.cl",
  "age": 30,
  "roles": ["admin", "researcher"]
}
```

---

### 3.4 GET /token/remaining - ¿Cuánto tiempo le queda a mi token?

**¿Para qué sirve?**  
Consultar cuántos segundos le quedan al token antes de expirar, sin necesidad de hacer un nuevo login. Útil para renovar proactivamente antes de que expire.

**Roles requeridos:** cualquier rol autenticado

**Ejemplo con curl:**
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

**Interpretación:**
- `expires_in_seconds`: segundos hasta que expira. Si es 0, el token ya expiró.
- `expires_at`: hora exacta de expiración (UTC).
- `issued_at`: hora en que se generó el token.

**Consejo:** Si `expires_in_seconds` < 300 (menos de 5 minutos), haz un nuevo `POST /login`.

---

### 3.5 POST /players - Crear nuevo usuario (solo admin)

**¿Para qué sirve?**  
Crear una nueva cuenta de usuario en el sistema LSG. Solo los administradores pueden hacer esto desde la API. El primer administrador debe crearse desde la consola del servidor.

**Roles requeridos:** `admin`

**Parámetros (body JSON):**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `name` | string | Sí | Nombre completo del jugador |
| `email` | string | Sí | Email único (será el username para login) |
| `password` | string | Sí | Contraseña en texto plano (se hashea con bcrypt) |
| `age` | integer | No | Edad del participante |
| `role` | string | No | Rol inicial: `player`, `teacher`, `researcher` o `admin`. Default: `player` |

**Ejemplo con curl:**
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
  "id_players": 54,
  "name": "María González",
  "email": "maria.gonzalez@usach.cl",
  "age": 22,
  "roles": ["player"]
}
```

**Errores comunes:**

| Código | Causa | Solución |
|--------|-------|----------|
| 400 | Email ya registrado | Usar otro email |
| 400 | Rol inválido | Usar player, teacher, researcher o admin |
| 403 | Token sin rol admin | Necesitas un token de administrador |

---

### 3.6 PATCH /admin/players/{id}/roles - Asignar o revocar un rol

**¿Para qué sirve?**  
Cambiar los roles de un jugador: agregar un nuevo rol (`grant`) o quitarle uno (`revoke`). Un jugador puede tener múltiples roles activos simultáneamente.

**Roles requeridos:** `admin`

**Parámetros de ruta:**

| Parámetro | Descripción |
|-----------|-------------|
| `{id}` | `id_players` del jugador a modificar |

**Body JSON:**

| Campo | Valores | Descripción |
|-------|---------|-------------|
| `role` | `player`, `teacher`, `researcher`, `admin` | Rol a asignar o revocar |
| `action` | `grant`, `revoke` | `grant` agrega el rol, `revoke` lo quita |

**Ejemplo - asignar rol researcher al jugador 54:**
```bash
curl -X PATCH 'https://lsg.diinf.usach.cl/lsg-auth/admin/players/54/roles' \
  -H 'Authorization: Bearer <token_admin>' \
  -H 'Content-Type: application/json' \
  -d '{"role": "researcher", "action": "grant"}'
```

**Respuesta exitosa (200):**
```json
{
  "status": "ok",
  "player_id": 54,
  "role": "researcher",
  "action": "grant"
}
```

**Ejemplo - revocar rol researcher del jugador 54:**
```bash
curl -X PATCH 'https://lsg.diinf.usach.cl/lsg-auth/admin/players/54/roles' \
  -H 'Authorization: Bearer <token_admin>' \
  -H 'Content-Type: application/json' \
  -d '{"role": "researcher", "action": "revoke"}'
```

**Notas:**
- `grant` es idempotente: si el rol ya existe, no lo duplica.
- `revoke` no borra el historial; marca el rol como revocado con timestamp.

---

### 3.7 GET /admin/players/{id}/roles - Ver historial de roles

**¿Para qué sirve?**  
Consultar todos los roles (activos y revocados) de un jugador, incluyendo quién los asignó y cuándo.

**Roles requeridos:** `admin`

**Parámetros:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `{id}` (ruta) | integer | `id_players` del jugador |
| `include_revoked` (query) | boolean | `true` (default): muestra todos. `false`: solo roles activos |

**Ejemplo - ver roles activos del jugador 54:**
```bash
curl -X GET 'https://lsg.diinf.usach.cl/lsg-auth/admin/players/54/roles?include_revoked=false' \
  -H 'Authorization: Bearer <token_admin>'
```

**Respuesta exitosa (200):**
```json
[
  {
    "id_player_role": 12,
    "role": "player",
    "assigned_at": "2026-05-01T10:00:00",
    "assigned_by": 26,
    "revoked_at": null,
    "is_active": true
  },
  {
    "id_player_role": 15,
    "role": "researcher",
    "assigned_at": "2026-05-07T09:30:00",
    "assigned_by": 26,
    "revoked_at": null,
    "is_active": true
  }
]
```

---

## 4. Preguntas frecuentes

**P: Mi token expiró, ¿qué hago?**  
R: Simplemente vuelve a hacer `POST /login`. El token dura 120 minutos.

**P: ¿Puedo tener varios roles al mismo tiempo?**  
R: Sí. Un usuario puede tener `player` y `researcher` simultáneamente. El sistema otorga el nivel de acceso del rol más alto.

**P: ¿Cómo sé cuál es mi `id_players`?**  
R: Usa `GET /whoami` y verás el campo `id_players` en la respuesta.

**P: ¿Por qué mi token no funciona en lsg-core-api?**  
R: Verifica que estás usando el formato exacto `Bearer <token>` en el header `Authorization`, y que el token no expiró (`GET /token/remaining`).