# Pipeline de Uso LSG-API por Rol
## LifeSync-Games

---

## Roles disponibles

| Rol | Descripción | Quién lo usa |
|-----|-------------|--------------|
| `admin` | Control total del sistema | Investigador principal |
| `researcher` | Análisis, exportación, ajuste de puntos | Equipo de investigación |
| `teacher` | Lectura de todos los jugadores | Docentes supervisores |
| `developer` | Integración de mods y videojuegos | Estudiantes/desarrolladores de mods |
| `player` | Uso personal del sistema | Participantes del estudio |

---

## Paso 0 — Autenticación (TODOS los roles)

```
POST /lsg-auth/login
  username = tu_email@usach.cl
  password = tu_contraseña
  ↓
  { "access_token": "eyJ..." }   ← válido 120 minutos

Renovar sin re-login:   POST /lsg-auth/token/refresh
Tiempo restante:        GET  /lsg-auth/token/remaining
Verificar perfil:       GET  /lsg-auth/whoami
```

---

## Rol: ADMIN — Pipeline completo

### A. Gestión de usuarios

```
┌─────────────────────────────────────────────────────────────────┐
│ CREAR USUARIOS                                                  │
│                                                                 │
│ Usuario individual:                                             │
│   POST /lsg-auth/players                                        │
│     { name, email, password, age, role }                        │
│                                                                 │
│ Lote temporal (para pruebas de developers):                     │
│   POST /lsg-auth/admin/players/batch-temp                       │
│     { count: 5, days_active: 14, role: "developer" }            │
│     → retorna emails + passwords (guardar inmediatamente)       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ GESTIÓN DE ROLES                                                │
│                                                                 │
│ Asignar:   PATCH /lsg-auth/admin/players/{id}/roles             │
│              { role: "researcher", action: "grant" }            │
│ Revocar:   PATCH /lsg-auth/admin/players/{id}/roles             │
│              { role: "researcher", action: "revoke" }           │
│ Historial: GET   /lsg-auth/admin/players/{id}/roles             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ CAMBIO DE CONTRASEÑA                                            │
│   PATCH /lsg-auth/admin/players/{id}/password                   │
│     { new_password: "nueva_contraseña_segura" }                 │
└─────────────────────────────────────────────────────────────────┘
```

### B. Configuración del sistema

```
┌─────────────────────────────────────────────────────────────────┐
│ VIDEOJUEGOS Y MECÁNICAS                                         │
│                                                                 │
│ 1. Crear videojuego:                                            │
│    POST /videogames                                             │
│      { name, genre, engine, type }                              │
│                                                                 │
│ 2. Crear mecánica en catálogo:                                  │
│    POST /videogames/mechanics/catalog                           │
│      { name, description, type }                                │
│    (type válido: "buff" o "nerf")                               │
│                                                                 │
│ 3. Vincular mecánica al juego:                                  │
│    POST /videogames/{game_id}/mechanics                         │
│      { id_modifiable_mechanic, options: {...} }                 │
│                                                                 │
│ 4. Carga masiva de mecánicas (Terraria, ~130):                  │
│    POST /videogames/{game_id}/mechanics/bulk                    │
│      { mechanics: [{name, description, type, options}...] }     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ATRIBUTOS Y DIMENSIONES DE PUNTOS                               │
│                                                                 │
│ GET/POST/PUT/DELETE /admin/attributes                           │
│ GET/POST/PUT/DELETE /admin/subattributes                        │
│ GET/POST/PUT/DELETE /admin/point-dimensions                     │
│ GET/POST/PUT/DELETE /admin/modifiable-mechanics                 │
│ GET/POST/PUT/DELETE /admin/modifiable-mechanics-videogames      │
│                                                                 │
│ Verificar integridad:                                           │
│   GET /admin/points/consistency-check                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ SENSORES                                                        │
│                                                                 │
│ 1. Crear proveedor: POST /sensors                               │
│ 2. Agregar endpoint: POST /sensors/{id}/endpoints               │
│ 3. Vincular a jugador: POST /sensors/players/{id}/link          │
│ 4. Activar endpoint:  POST /sensors/players/{id}/link-endpoint  │
└─────────────────────────────────────────────────────────────────┘
```

### C. Ajuste de puntos

```
┌─────────────────────────────────────────────────────────────────┐
│ CARGAR PUNTOS DIRECTAMENTE A UN JUGADOR                         │
│                                                                 │
│   POST /players/{id}/points/adjust                              │
│     {                                                           │
│       "point_dimension_id": 1,   ← ID de la dimensión           │
│       "direction": "CREDIT",     ← CREDIT suma, DEBIT resta     │
│       "amount": 100,                                            │
│       "reason": "Ajuste manual por...",                         │
│       "videogame_id": 14                                        │
│     }                                                           │
│                                                                 │
│ Fuentes de puntos (source_type):                                │
│   SENSOR     → desde sensor_ingest_event (automático)           │
│   REDEMPTION → canje de mecánica (automático)                   │
│   ADJUST     → ajuste manual del admin/researcher               │
│   OFFLINE_GAME → sincronización offline del mod                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Rol: RESEARCHER — Pipeline de investigación

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. SETUP INICIAL (una vez por estudio)                          │
│                                                                 │
│   a) Verificar jugadores: GET /players?page=1&page_size=50      │
│   b) Inicializar atributos por participante:                    │
│      POST /players/{id}/attributes/init                         │
│   c) Verificar goalposts IC²:                                   │
│      GET /ic2/goalposts?version_tag=v1.0                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2. OPERACIÓN DURANTE EL ESTUDIO                                 │
│                                                                 │
│   Ajuste de puntos:                                             │
│     POST /players/{id}/points/adjust                            │
│                                                                 │
│   Calcular IC² de un participante:                              │
│     POST /ic2/compute                                           │
│       {                                                         │
│         "player_id": 46,                                        │
│         "version_tag": "v1.0",                                  │
│         "experiment_tag": "LSG_C1_T1_CV",                       │
│         "session_time_minutes": 45,                             │
│         "signals": { MVPA_min_week, steps_day, ... }            │
│       }                                                         │
│                                                                 │
│   Ver resumen IC² por condición:                                │
│     GET /analytics/ic2/summary?experiment_tag=LSG_C1_T1_CV      │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ 3. EXPORTACIÓN (análisis R/Python)                               │
│                                                                  │
│   GET /research/export/ic2?experiment_tag=LSG_C1_T1_CV&format=csv│
│   GET /research/export/points?experiment_tag=...&format=csv      │
│   GET /research/export/sessions?format=csv                       │
│   GET /research/export/sensors?format=csv                        │
│                                                                  │
│   Todos retornan player_pseudo = LSG-PXXX (no nombres reales)    │
└──────────────────────────────────────────────────────────────────┘
```

---

## Rol: DEVELOPER — Pipeline de integración de mod

```
┌─────────────────────────────────────────────────────────────────┐
│ FASE 1: EXPLORACIÓN (antes de integrar)                         │
│                                                                 │
│ Ver catálogo de juegos:   GET /videogames                       │
│ Ver mis mecánicas:        GET /videogames/{id}/mechanics        │
│ Ver atributos:            GET /attributes-map                   │
│ Ver goalposts IC²:        GET /ic2/goalposts                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ FASE 2: REGISTRAR EL VIDEOJUEGO (si no existe)                  │
│                                                                 │
│ 1. POST /videogames                                             │
│      { "name": "Mi Juego", "genre": "rpg", "engine": "Unity" }  │
│    → guarda el id_videogame                                     │
│                                                                 │
│ 2. POST /videogames/{id}/mechanics/bulk                         │
│      { "mechanics": [                                           │
│          { "name": "Speed Boost", "type": "buff",               │
│            "options": {"multiplier": 1.2} },                    │
│          { "name": "HP Penalty", "type": "nerf",                │
│            "options": {"reduction": 0.15} }                     │
│      ]}                                                         │
│    → guarda id_modifiable_mechanic_videogame por mecánica       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ FASE 3: VINCULAR JUGADOR AL JUEGO (en el mod, al iniciar)       │
│                                                                 │
│ POST /videogames/{game_id}/players/{player_id}/connect          │
│   { "lsg_enabled": true, "plugin_version": "1.0.0" }            │
│                                                                 │
│ → después de esto el jugador puede ganar/gastar puntos          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ FASE 4: SESIÓN DE JUEGO (en el mod, al abrir/cerrar el juego)   │
│                                                                 │
│ Al abrir:                                                       │
│   POST /videogames/{id}/players/{pid}/sessions                  │
│     { "plugin_version": "1.0.0" }                               │
│     → guarda id_session                                         │
│                                                                 │
│ Al cerrar:                                                      │
│   PATCH /videogames/{id}/players/{pid}/sessions/{sid}/end       │
│     {}                                                          │
│     → calcula duration_seconds automáticamente                  │
│     → registra en interaction_logs                              │
│                                                                 │
│ ¿Se puede automatizar? SÍ — el mod puede llamar estos           │
│ endpoints al detectar el evento de inicio/cierre del juego.     │
│ No requiere acción del usuario.                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ FASE 5: PUNTOS — CARGAR Y CANJEAR                               │
│                                                                 │
│ PLAN A — vía sensor (automático con sensor configurado):        │
│   POST /sensors/ingest/webhook                                  │
│     { player_id, sensor_endpoint_id, players_sensor_endpoint_id │
│       raw_payload: { "steps": 8500, "date": "2026-05-07" },     │
│       parsed_value: 8500.0 }                                    │
│   → el sensor queda registrado, puntos se asignan via pipeline  │
│                                                                 │
│ PLAN B — carga directa de puntos (sin sensor):                  │
│   POST /players/{id}/points/adjust   (requiere researcher/admin)│
│     { point_dimension_id, direction: "CREDIT", amount, reason } │
│   → fuente queda como "ADJUST", registrado en interaction_logs  │
│   → usar cuando el developer procesa los datos externamente     │
│                                                                 │
│ PLAN C — offline (juego sin conexión):                          │
│   POST /offline/sync                                            │
│     { player_id, game_id, events: [                             │
│         { client_ref: "uuid", client_generated_at: "...",       │
│           point_dimension_id: 1, direction: "CREDIT",           │
│           amount: 45, source_type: "OFFLINE_GAME" }             │
│     ]}                                                          │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ FASE 6: CANJE DE MECÁNICA (el jugador "compra" un buff)          │
│                                                                  │
│ 1. Preview (verificar si tiene puntos suficientes):              │
│    POST /videogames/{id}/players/{pid}/redeem/preview            │
│      { modifiable_mechanic_videogame_id: 5,                      │
│        point_dimension_id: 1, amount: 50 }                       │
│    → retorna can_redeem, current_balance, resulting_balance      │
│                                                                  │
│ 2. Confirmar canje:                                              │
│    POST /videogames/{id}/players/{pid}/redeem                    │
│      (mismo body)                                                │
│    → descuenta puntos + registra evento                          │
│                                                                  │
│ 3. El mod activa el buff según el id_modifiable_mechanic canjeado│
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ FASE 7: VERIFICAR ESTADO DEL JUGADOR                            │
│                                                                 │
│ Balance de puntos:   GET /players/{id}/points/balance           │
│ Historial IC²:       GET /ic2/history?player_id={id}            │
│ Timeline completo:   GET /players/{id}/timeline                 │
│ Historial de canjes: GET /points/ledger?source_type=REDEMPTION  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Rol: TEACHER — Pipeline de supervisión

```
┌─────────────────────────────────────────────────────────────────┐
│ SUPERVISIÓN DE PARTICIPANTES                                    │
│                                                                 │
│ Ver todos los jugadores: GET /players                           │
│ Detalle + roles:         GET /players/{id}                      │
│ Timeline de actividad:   GET /players/{id}/timeline             │
│ Balance de puntos:       GET /players/{id}/points/balance       │
│ Juegos del jugador:      GET /players/{id}/games                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ANALÍTICAS                                                      │
│                                                                 │
│ GET /analytics/player-game-overview                             │
│ GET /analytics/points-balance                                   │
│ GET /analytics/player-attribute-balance                         │
│ GET /analytics/games/time-to-first-redeem                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Rol: PLAYER — Pipeline del participante

```
┌─────────────────────────────────────────────────────────────────┐
│ VER MI INFORMACIÓN                                              │
│                                                                 │
│ Mi perfil:          GET /players/{mi_id}                        │
│ Mis puntos:         GET /players/{mi_id}/points/balance         │
│ Mis juegos:         GET /players/{mi_id}/games                  │
│ Mi historial IC²:   GET /ic2/history?player_id={mi_id}          │
│ Mi timeline:        GET /players/{mi_id}/timeline               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ACCIONES EN EL JUEGO (el mod llama esto automáticamente)        │
│                                                                 │
│ Ver mecánicas disponibles:  GET /videogames/{id}/mechanics      │
│ Preview de canje:           POST .../redeem/preview             │
│ Canjear mecánica:           POST .../redeem                     │
│ Sincronizar offline:        POST /offline/sync                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Formulario de solicitud de nuevos endpoints

Ver archivo `FORM_APPLICATION_ENDPOINTS.md` adjunto.