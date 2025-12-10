# Estructura del proyecto

```
lsg-auth/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── db.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   └── cli_create_user.py
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
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