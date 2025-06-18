from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class StatusProcesso(enum.Enum):
    EM_ANDAMENTO = "em_andamento"
    FINALIZADO = "finalizado"
    AGUARDANDO_ASSINATURA = "aguardando_assinatura"
    ASSINADO = "assinado"

class Processo(Base):
    __tablename__ = "processos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    status = Column(Enum(StatusProcesso), default=StatusProcesso.EM_ANDAMENTO)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    arquivos = relationship("Arquivo", back_populates="processo", cascade="all, delete-orphan")