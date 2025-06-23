from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class DocumentoAssinatura(Base):
    __tablename__ = "documentos_assinatura"

    id = Column(Integer, primary_key=True, index=True)
    processo_id = Column(Integer, ForeignKey("processos.id"), nullable=False)
    documento_id_autentique = Column(String, nullable=False)  # ID retornado pelo Autentique
    nome_documento = Column(String, nullable=False)
    status = Column(String, nullable=False, default="aguardando_assinatura")  # status do documento no Autentique
    data_upload = Column(DateTime(timezone=True), server_default=func.now())

    processo = relationship("Processo", back_populates="documentos_assinatura")
    assinaturas = relationship("AssinaturaSignatario", back_populates="documento_assinatura", cascade="all, delete-orphan")