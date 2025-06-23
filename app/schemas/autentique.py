from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field

class PositionInput(BaseModel):
    x: str
    y: str
    z: int
    element: str

class SignerInput(BaseModel):
    name: str
    email: str
    positions: List[PositionInput]

class DocumentoAutentiqueInput(BaseModel):
    nome_documento: str = Field(..., description="Nome do documento a ser criado no Autentique")
    arquivo_cloudinary: HttpUrl = Field(..., description="URL completa do arquivo PDF no Cloudinary")
    cc_email: str = Field(..., description="E-mail para cópia (CC)")
    signers: List[SignerInput] = Field(..., description="Lista de signatários do documento")

class SignerOutput(BaseModel):
    public_id: str
    name: str
    email: str
    link_assinatura: Optional[str]

class DocumentoAutentiqueOutput(BaseModel):
    document_id: str
    nome: str
    signers: List[SignerOutput]