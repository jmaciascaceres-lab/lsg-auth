from sqlalchemy import Column, Integer, String, DateTime, func
from .db import Base


class Player(Base):
    __tablename__ = "players"

    id_players = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    password_hash = Column(String(95), nullable=False)
    email = Column(String(128), nullable=False, unique=True, index=True)
    age = Column(Integer, nullable=True)
    external_type = Column(String(16), nullable=True)
    external_id = Column(Integer, nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
