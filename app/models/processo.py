from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class StatusProcesso(enum.Enum):
    AGUARDANDO_RASTER_MOTORISTA = "aguardando_raster_motorista"
    AGUARDANDO_RASTER_CAMINHAO = "aguardando_raster_caminhao"
    AGUARDANDO_ASSINATURA_CONTRATO = "aguardando_assinatura_contrato"
    AGUARDANDO_CTE = "aguardando_cte"
    AGUARDANDO_MANIFESTO = "aguardando_manifesto"
    AGUARDANDO_RNTRC = "aguardando_rntrc"
    AGUARDANDO_COMPROVANTE = "aguardando_comprovante"
    FINALIZADO = "finalizado"
    REJEITADO = "rejeitado"

class Processo(Base):
    __tablename__ = "processos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    numero_contrato = Column(String, unique=True, nullable=False)
    status = Column(Enum(StatusProcesso), default=StatusProcesso.AGUARDANDO_RASTER_MOTORISTA)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    arquivos = relationship("Arquivo", back_populates="processo", cascade="all, delete-orphan")
    documentos_assinatura = relationship("DocumentoAssinatura", back_populates="processo", cascade="all, delete-orphan")