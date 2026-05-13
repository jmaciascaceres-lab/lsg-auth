from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    func, Computed,
)
from sqlalchemy.orm import relationship
from .db import Base


class Player(Base):
    __tablename__ = "players"

    id_players    = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name          = Column(String(50),  nullable=False)
    password_hash = Column(String(95),  nullable=True)   # nullable: BD permite auth externa
    email         = Column(String(128), nullable=False, unique=True, index=True)
    age           = Column(Integer,     nullable=True)
    external_type = Column(String(16),  nullable=True)
    external_id   = Column(String(128), nullable=True)
    updated_at    = Column(
        DateTime,
        nullable=True,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_at    = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    temp_expires_at = Column(DateTime, nullable=True, default=None)

    _roles = relationship(
        "PlayerRole",
        back_populates="_player",
        lazy="select",
        cascade="all, delete-orphan",
    )

    @property
    def roles(self) -> list:
        """Retorna lista de strings con los roles activos (revoked_at IS NULL)."""
        return [r.role for r in self._roles if r.revoked_at is None]

    @property
    def is_temp_expired(self) -> bool:
        """True si es cuenta temporal y ya expiró."""
        if self.temp_expires_at is None:
            return False
        return datetime.utcnow() > self.temp_expires_at


class PlayerRole(Base):
    __tablename__ = "player_roles"

    id_player_role = Column(Integer, primary_key=True, autoincrement=True)
    id_players     = Column(Integer, ForeignKey("players.id_players"), nullable=False)
    role           = Column(String(32), nullable=False)
    assigned_at    = Column(DateTime,   nullable=False, server_default=func.now())
    assigned_by    = Column(Integer,    nullable=True)   # id_players del admin
    revoked_at     = Column(DateTime,   nullable=True, default=None)

    # Relación inversa hacia Player
    _player = relationship("Player", back_populates="_roles")