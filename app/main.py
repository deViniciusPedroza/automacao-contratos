from fastapi import FastAPI
from app.database import Base, engine

# Importar suas rotas (quando forem criadas)
# from app.routers import exemplo_router

app = FastAPI()

# Criar tabelas (somente para fase inicial, depois migrar para Alembic)
Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"message": "API funcionando!"}

# Registrar rotas (exemplo futuro)
# app.include_router(exemplo_router.router)
