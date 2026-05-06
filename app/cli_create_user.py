import argparse
from sqlalchemy.orm import Session

from .db import SessionLocal, Base, engine
from . import models
from .auth import hash_password

VALID_ROLES = {"player", "teacher", "researcher", "admin"}


def create_player_cli(
    name:     str,
    email:    str,
    password: str,
    age:      int | None,
    role:     str,
) -> None:
    """
    Crea un jugador directamente en BD, sin pasar por el endpoint HTTP.
    Útil para bootstrap del primer admin o para entornos de CI.

    El rol se inserta en player_roles con assigned_by=NULL (bootstrap CLI).
    """
    if role not in VALID_ROLES:
        print(f"Error: rol '{role}' inválido. Valores permitidos: {sorted(VALID_ROLES)}")
        return

    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        player = models.Player(
            name          = name,
            email         = email,
            password_hash = hash_password(password),
            age           = age,
        )
        db.add(player)
        db.flush()

        role_record = models.PlayerRole(
            id_players  = player.id_players,
            role        = role,
            assigned_by = None,
        )
        db.add(role_record)

        db.commit()
        db.refresh(player)
        print(
            f"[OK] Jugador creado → "
            f"id_players={player.id_players}, "
            f"email={player.email}, "
            f"rol={role}"
        )

    except Exception as e:
        db.rollback()
        print(f"[ERROR] No se pudo crear el jugador: {e}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crear jugador LSG desde CLI (uso: bootstrap o CI)."
    )
    parser.add_argument("--name",     required=True,  help="Nombre del jugador")
    parser.add_argument("--email",    required=True,  help="Email del jugador")
    parser.add_argument("--password", required=True,  help="Contraseña en texto plano")
    parser.add_argument("--age",      type=int, default=None, help="Edad (opcional)")
    parser.add_argument(
        "--role",
        type=str,
        default="player",
        choices=list(VALID_ROLES),
        help="Rol inicial del jugador (default: player)",
    )

    args = parser.parse_args()
    create_player_cli(
        name     = args.name,
        email    = args.email,
        password = args.password,
        age      = args.age,
        role     = args.role,
    )


if __name__ == "__main__":
    main()