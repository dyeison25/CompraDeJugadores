from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UsuarioModelo(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    rol: Mapped[str] = mapped_column(String(10))
    __table_args__ = (
        CheckConstraint("rol IN ('admin','usuario')", name="ck_usuario_rol"),
        Index("uq_usuario_email_normalizado", func.lower(email), unique=True),
    )


class JugadorModelo(Base):
    __tablename__ = "jugadores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    equipo: Mapped[str] = mapped_column(String(80))
    nacionalidad: Mapped[str] = mapped_column(String(50))
    edad: Mapped[int] = mapped_column(Integer)
    posicion: Mapped[str] = mapped_column(String(20))
    precio_centimos: Mapped[int] = mapped_column(BigInteger)
    foto: Mapped[str] = mapped_column(String(1000))
    dorsal: Mapped[int] = mapped_column(Integer)
    descripcion: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(12), index=True)
    destacado: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        CheckConstraint("precio_centimos > 0", name="ck_jugador_precio"),
        CheckConstraint("edad BETWEEN 16 AND 55", name="ck_jugador_edad"),
        CheckConstraint("dorsal BETWEEN 1 AND 99", name="ck_jugador_dorsal"),
        CheckConstraint("estado IN ('disponible','vendido')", name="ck_jugador_estado"),
        CheckConstraint("version > 0", name="ck_jugador_version"),
        CheckConstraint("destacado IN (0,1)", name="ck_jugador_destacado"),
    )


class CompraModelo(Base):
    __tablename__ = "compras"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), index=True)
    jugador_id: Mapped[int] = mapped_column(ForeignKey("jugadores.id", ondelete="RESTRICT"), unique=True)
    precio_centimos: Mapped[int] = mapped_column(BigInteger)
    fecha: Mapped[str] = mapped_column(String(30))
    jugador_nombre: Mapped[str] = mapped_column(String(80))
    equipo: Mapped[str] = mapped_column(String(80))
    foto: Mapped[str] = mapped_column(String(1000))
    __table_args__ = (CheckConstraint("precio_centimos > 0", name="ck_compra_precio"),)
