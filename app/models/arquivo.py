from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class TipoArquivo(enum.Enum):
    INDIVIDUAL = "individual"
    FINAL = "final"

class Arquivo(Base):
    __tablename__ = "arquivos"

    id = Column(Integer, primary_key=True, index=True)
    processo_id = Column(Integer, ForeignKey("processos.id"), nullable=False)
    etapa = Column(String, nullable=False)  # Ex: raster, contratos, etc
    public_id = Column(String, nullable=False, unique=True)
    url = Column(String, nullable=False)
    tipo = Column(Enum(TipoArquivo), default=TipoArquivo.INDIVIDUAL)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    processo = relationship("Processo", back_populates="arquivos")