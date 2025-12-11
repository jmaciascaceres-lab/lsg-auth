# LSG-AUTH

Servicio de autenticación para LifeSync-Games (LSG), basado en **FastAPI**, **MySQL** y **JWT**.  

Provee:

- Registro de jugadores con contraseña hasheada usando **bcrypt**.
- Inicio de sesión con verificación bcrypt.
- Emisión de **JSON Web Tokens (JWT)**.
- Endpoint protegido (`/whoami`) para obtener el jugador autenticado.
- Healthcheck de la API y de la conexión a la base de datos.

---

## Estructura del proyecto

```text
lsg-auth/
│
├── app/
│   ├── tools/
│   │   └── generate_jwt_secret.py   # script local para generar JWT_SECRET_KEY (ignorado por git)
│   ├── __init__.py
│   ├── auth.py                      # bcrypt + JWT (hash_password, verify_password, create_access_token, etc.)
│   ├── cli_create_user.py           # CLI para crear jugadores desde terminal
│   ├── db.py                        # conexión SQLAlchemy a MySQL, variables de entorno
│   ├── main.py                      # FastAPI: /health, /players, /login, /whoami
│   ├── models.py                    # ORM Player
│   └── schemas.py                   # Pydantic schemas (PlayerCreate, PlayerOut, Token, etc.)
│
├── .env.example                     # plantilla de variables de entorno (sin credenciales reales)
├── .gitignore
├── docker-compose.yml               # opcional: MySQL local para desarrollo
├── Dockerfile
├── README.md
└── requirements.txt
```

## Esquema mínimo de la tabla players

```sql
CREATE TABLE players (
    id_players      INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(50) NOT NULL,
    password_hash   CHAR(95) NOT NULL,
    email           VARCHAR(128) NOT NULL UNIQUE,
    age             INT,
    external_type   VARCHAR(16),
    external_id     INT,
    updated_at      TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

## Variables de entorno

```env
# ===== Base de datos MySQL =====
DB_HOST=127.0.0.1           # host local (túnel SSH)
DB_PORT=3307                # puerto local mapeado al 3306 interno
DB_USER=USUARIO
DB_PASSWORD=PASSWORD
DB_NAME=BASE_DE_DATOS

# ===== JWT =====
JWT_SECRET_KEY=VALOR_LARGO_Y_ALEATORIO_GENERADO
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
```

### Generar JWT_SECRET_KEY

```bash
python -m app.tools.generate_jwt_secret.py
```

Nota: copiar el valor generado y pegarlo en el archivo .env

## Pre-requisitos

- Python 3.11+
- (Opcional) Docker + Docker Compose, si se desea usar MySQL local
- Git

### Instalación y ejecución (sin Docker)

```bash
cd lsg-auth

# Crear y activar entorno virtual (PowerShell)
python -m venv .venv

# Activar entorno virtual (PowerShell)
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install python-multipart

# Copiar plantilla y configurar .env
cp .env.example .env
# (editar .env con tus credenciales y JWT_SECRET_KEY)

# Levantar API
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Probar los endpoints desde: http://localhost:8000/
```

### Instalación y ejecución (con Docker)    

```bash
docker-compose up --build
```

Nota: La API se expondrá en `http://localhost:8000` y el MySQL local en `localhost:3306`

### Endpoints

- `/health`: Healthcheck de la API
- `/players`: Gestión de jugadores
- `/login`: Inicio de sesión
- `/whoami`: Información del jugador autenticado