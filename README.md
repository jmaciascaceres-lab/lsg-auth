# Estructura del proyecto

```text
lsg-auth/
│
├── app/
│   ├── tools/
│   │   └── generate_jwt_secret.py   # script local, ignorado por git
│   ├── __init__.py
│   ├── auth.py                      # bcrypt + JWT
│   ├── cli_create_user.py           # CLI para crear jugadores
│   ├── db.py                        # conexión SQLAlchemy a MySQL (env)
│   ├── main.py                      # FastAPI: /health, /players, /login, /whoami
│   ├── models.py                    # ORM Player
│   └── schemas.py                   # Pydantic schemas
│
├── .env.example                     # plantilla sin credenciales
├── .gitignore
├── docker-compose.yml               # opcional para MySQL local
├── Dockerfile
├── README.md
└── requirements.txt
```

## Esquema equivalente para PostgreSQL

```sql
CREATE TABLE players (
    id_players      SERIAL PRIMARY KEY,
    name            VARCHAR(50) NOT NULL,
    password_hash   CHAR(95)    NOT NULL,
    email           VARCHAR(128) NOT NULL UNIQUE,
    age             INT,
    external_type   VARCHAR(16),
    external_id     INT,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## Variables de entorno

```env
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres
```

## Ejecución

```bash
docker-compose up --build
```

### Ejemplo

```bash
python cli_create_user.py --name "user1" --email "user1@example.com" --password "miclavesegura1" --age 35
```