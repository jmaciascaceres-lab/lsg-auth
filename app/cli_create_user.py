import argparse
from sqlalchemy.orm import Session

from .db import SessionLocal, Base, engine
from . import models
from .auth import hash_password


def create_player_cli(name: str, email: str, password: str, age: int | None):
    # Asegurar que la tabla exista
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        player = models.Player(
            name=name,
            email=email,
            password_hash=hash_password(password),
            age=age,
            role="player",
        )
        db.add(player)
        db.commit()
        db.refresh(player)
        print(f"Jugador creado con id_players={player.id_players}")
    except Exception as e:
        db.rollback()
        print(f"Error creando jugador: {e}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Crear jugador LSG desde CLI")
    parser.add_argument("--name", required=True, help="Nombre del jugador")
    parser.add_argument("--email", required=True, help="Email del jugador")
    parser.add_argument("--password", required=True, help="Contraseña en texto plano")
    parser.add_argument("--age", type=int, default=None, help="Edad (opcional)")
    parser.add_argument("--role", type=str, default="player", help="Role (opcional)")

    args = parser.parse_args()

    create_player_cli(
        name=args.name,
        email=args.email,
        password=args.password,
        age=args.age,
        role=args.role,
    )


if __name__ == "__main__":
    main()
