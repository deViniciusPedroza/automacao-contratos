from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class AssinaturaSignatario(Base):
    __tablename__ = "assinaturas_signatarios"

    id = Column(Integer, primary_key=True, index=True)
    documento_assinatura_id = Column(Integer, ForeignKey("documentos_assinatura.id"), nullable=False)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False)
    telefone = Column(String, nullable=True)  
    email_secundario = Column(String, nullable=True)  
    link_assinatura = Column(String, nullable=True)
    tipo_acesso = Column(String, nullable=True)
    status_assinatura = Column(String, nullable=False, default="aguardando")
    data_assinatura = Column(DateTime(timezone=True), nullable=True)

    documento_assinatura = relationship("DocumentoAssinatura", back_populates="assinaturas")