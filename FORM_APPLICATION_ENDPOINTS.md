# Formulario de Solicitud y Reporte - LSG-API

Enviar a: **joaquin.macias@usach.cl** (responsable de investigación) | Asunto: `[LSG-API] Solicitud / Incidencia`

---

## FORMULARIO A - Solicitud de nuevo endpoint

```
Fecha:              _______________
Nombre:             _______________
Rol en el proyecto: _______________  (developer / researcher / teacher)
Repositorio/Mod:    _______________

1. DESCRIPCIÓN DEL ENDPOINT SOLICITADO

Método HTTP:     [ ] GET   [ ] POST   [ ] PATCH   [ ] PUT   [ ] DELETE

Ruta propuesta:  /lsg-core-api/_______________
                 /lsg-auth/_______________

¿Para qué sirve? (qué problema resuelve)
___________________________________________________________________________
___________________________________________________________________________

¿Quién lo usaría? (rol/s)
[ ] player   [ ] teacher   [ ] researcher   [ ] developer   [ ] admin

2. DATOS DE ENTRADA (Request)

Parámetros en la URL (ej: :player_id, :game_id):
___________________________________________________________________________

Body JSON de ejemplo:
{
  ___________________________________________________________________________
}

3. DATOS DE SALIDA (Response)

Respuesta esperada (campos y formato):
{
  ___________________________________________________________________________
}

4. CONTEXTO ADICIONAL

¿Ya existe un endpoint parecido? _______________
¿Con qué frecuencia se usaría? (ej: cada sesión, una vez por jugador)
___________________________________________________________________________

¿Es bloqueante para tu integración? [ ] Sí - urgente   [ ] No - mejora futura

Prioridad sugerida:  [ ] Alta   [ ] Media   [ ] Baja
```

---

## FORMULARIO B - Reporte de incidencia / bug

```
Fecha y hora:    _______________
Nombre:          _______________
Servicio:        [ ] LSG-Auth   [ ] LSG-Core-API

1. DESCRIPCIÓN DE LA INCIDENCIA 

Endpoint afectado:  _______________  (ej: POST /sensors/ingest/webhook)
Código de respuesta recibido:  _______________  (ej: 400, 500)

Descripción breve del problema:
___________________________________________________________________________
___________________________________________________________________________

2. REPRODUCCIÓN

Pasos para reproducir:
1. ___________________________________________________________________________
2. ___________________________________________________________________________
3. ___________________________________________________________________________

Curl / body enviado:
```bash
curl -X ___ '...' \
  -d '{
    ___________________________________________________________________________
  }'
```

Respuesta recibida (copiar el "Response body"):
```json
{
  ___________________________________________________________________________
}
```

3. COMPORTAMIENTO ESPERADO

¿Qué debería haber retornado?
___________________________________________________________________________

4. CONTEXTO

¿Ocurre siempre o es intermitente?  [ ] Siempre   [ ] Intermitente
¿Afecta a otros usuarios?           [ ] Solo a mí  [ ] Varios jugadores
Fecha en que empezó el problema:    _______________

Impacto:  [ ] Bloqueante - no puedo continuar   [ ] Degradado - workaround disponible
```

---

## Plantilla de correo rápido

**Para incidencia urgente:**

```
Asunto: [LSG-API URGENTE] Bug en POST /sensors/ingest/webhook

Hola equipo,

Encontré una incidencia en el endpoint: POST /sensors/ingest/webhook

Error: 400 - "PLAYERS_SENSOR_ENDPOINT_NOT_FOUND"
Body enviado: { ... }
Respuesta: { "detail": "..." }

Impacto: No puedo registrar datos de sensor.

Saludos,
[Nombre]
```

**Para solicitud de endpoint:**

```
Asunto: [LSG-API] Solicitud: GET /videogames/{id}/players - listar jugadores de un juego

Hola equipo,

Necesitaría un endpoint que me permita ver todos los jugadores vinculados
a un videojuego específico. Lo usaría en el mod para sincronizar
el estado de la sesión al inicio.

Ruta propuesta: GET /videogames/{game_id}/players
Roles: developer, researcher, admin
Respuesta esperada: lista de {id_players, name, lsg_enabled}

¿Es factible agregarlo?

Saludos,
[Nombre]
```