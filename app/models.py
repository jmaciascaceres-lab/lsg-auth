from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from .db import Base


class Player(Base):
    __tablename__ = "players"

    id_players    = Column(Integer, primary_key=True, index=True)
    name          = Column(String(50),  nullable=False)
    password_hash = Column(String(95),  nullable=False)
    email         = Column(String(128), nullable=False, unique=True, index=True)
    age           = Column(Integer,     nullable=True)
    external_type = Column(String(16),  nullable=True)
    external_id   = Column(Integer,     nullable=True)
    updated_at    = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_at    = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    _roles = relationship(
        "PlayerRole",
        foreign_keys="[PlayerRole.id_players]",
        lazy="selectin",
    )

    @property
    def roles(self) -> list:
        """
        Lista de nombres de roles activos (revoked_at IS NULL).
        Usada por los schemas Pydantic y por require_roles().
        """
        return [pr.role for pr in self._roles if pr.revoked_at is None]


class PlayerRole(Base):
    """
    Tabla player_roles: un jugador puede tener N roles activos.
    Un rol se "revoca" seteando revoked_at (no se borra la fila → historial).
    Creada por PATCH-01 de la migración LSG v1.1.
    """
    __tablename__ = "player_roles"

    id_player_role = Column(Integer, primary_key=True, autoincrement=True)
    id_players     = Column(
        Integer,
        ForeignKey("players.id_players"),
        nullable=False,
        index=True,
    )
    role           = Column(String(32), nullable=False)
    assigned_at    = Column(DateTime, nullable=False, server_default=func.now())
    assigned_by    = Column(
        Integer,
        ForeignKey("players.id_players"),
        nullable=True,
        comment="id_players del admin que asignó el rol. NULL = asignado vía CLI.",
    )
    revoked_at     = Column(
        DateTime,
        nullable=True,
        comment="NULL = rol activo. Timestamp = rol revocado.",
    )