from fastapi import FastAPI
from app.database import Base, engine
from app.routers import upload

# Importar suas rotas (quando forem criadas)
# from app.routers import exemplo_router

app = FastAPI()

app.include_router(upload.router)

# Criar tabelas (somente para fase inicial, depois migrar para Alembic)
Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"message": "API funcionando!"}

# Registrar rotas (exemplo futuro)
# app.include_router(exemplo_router.router)
