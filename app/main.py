from fastapi import FastAPI
from app.database import Base, engine
from app.routers import upload
from app.routers import cloudinary_file_router  # Importa o novo router

app = FastAPI()

app.include_router(upload.router)
app.include_router(cloudinary_file_router.router)  # Inclui o novo router

# Criar tabelas (somente para fase inicial, depois migrar para Alembic)
Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"message": "API funcionando!"}