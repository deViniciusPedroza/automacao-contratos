from fastapi import FastAPI
from app.database import Base, engine
# importação das rotas
from app.routers import upload
from app.routers import cloudinary_file_router
from app.routers import processo
from app.routers import autentique
from app.routers import sincronizacao
# importação dos modelos
from app.models.processo import Processo
from app.models.arquivo import Arquivo
from app.models.assinatura_signatario import AssinaturaSignatario
from app.models.documento_assinatura import DocumentoAssinatura

app = FastAPI()

app.include_router(upload.router)
app.include_router(cloudinary_file_router.router)
app.include_router(processo.router)
app.include_router(autentique.router)
app.include_router(sincronizacao.router)

# Criar tabelas (somente para fase inicial, depois migrar para Alembic)
Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"message": "API funcionando!"}