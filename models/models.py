"""Modelos SQLAlchemy: perfis de empresas e editais já notificados."""
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database.db import Base


class EmpresaPerfil(Base):
    """Perfil de interesse cadastrado por uma empresa para monitoramento de licitações."""

    __tablename__ = "empresas_perfis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome_empresa = Column(String(255), nullable=False)

    # Armazenadas como texto separado por vírgula (ex: "software, nuvem, licenças")
    palavras_chave_positivas = Column(Text, nullable=False, default="")
    palavras_chave_negativas = Column(Text, nullable=True, default="")

    # UFs separadas por vírgula (ex: "SP,RJ,MG"). Vazio = âmbito nacional (todas UFs)
    estados = Column(String(255), nullable=True, default="")

    valor_minimo = Column(Float, nullable=True, default=0)
    valor_maximo = Column(Float, nullable=True, default=0)

    telegram_token = Column(String(255), nullable=True)
    telegram_chat_id = Column(String(100), nullable=True)

    criado_em = Column(DateTime, default=datetime.utcnow)

    editais_notificados = relationship(
        "EditalNotificado", back_populates="empresa", cascade="all, delete-orphan"
    )

    def lista_palavras_positivas(self):
        return [p.strip().lower() for p in self.palavras_chave_positivas.split(",") if p.strip()]

    def lista_palavras_negativas(self):
        if not self.palavras_chave_negativas:
            return []
        return [p.strip().lower() for p in self.palavras_chave_negativas.split(",") if p.strip()]

    def lista_estados(self):
        if not self.estados:
            return []
        return [uf.strip().upper() for uf in self.estados.split(",") if uf.strip()]


class EditalNotificado(Base):
    """Registro de um edital já processado/alertado para uma empresa, evitando duplicidade."""

    __tablename__ = "editais_notificados"
    __table_args__ = (
        UniqueConstraint("empresa_id", "numero_controle_pncp", name="uq_empresa_edital"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas_perfis.id"), nullable=False)

    numero_controle_pncp = Column(String(100), nullable=False)
    orgao = Column(String(500), nullable=True)
    objeto = Column(Text, nullable=True)
    valor_estimado = Column(Float, nullable=True)
    data_sessao = Column(String(50), nullable=True)
    link = Column(String(500), nullable=True)

    notificado_em = Column(DateTime, default=datetime.utcnow)

    empresa = relationship("EmpresaPerfil", back_populates="editais_notificados")
