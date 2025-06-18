from fastapi import FastAPI
from app.database import Base, engine
from app.routers import upload
from app.routers import cloudinary_file_router
from app.routers import processo

# IMPORTANTE: Importe os modelos para garantir que as tabelas sejam criadas
from app.models.processo import Processo
from app.models.arquivo import Arquivo

app = FastAPI()

app.include_router(upload.router)
app.include_router(cloudinary_file_router.router)
app.include_router(processo.router)

# Criar tabelas (somente para fase inicial, depois migrar para Alembic)
Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"message": "API funcionando!"}