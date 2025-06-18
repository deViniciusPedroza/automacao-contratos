# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Substitua pela sua string de conexão do Render
DATABASE_URL = "postgresql://raklog_postgresql_user:gl3oJ9qNd2XapCdq4h1hUWOQQy5x8OHB@dpg-d1883iogjchc73dsp830-a.ohio-postgres.render.com/raklog_postgresql"

# Criação do engine de conexão com o banco
engine = create_engine(DATABASE_URL)

# Criação da fábrica de sessões
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos ORM
Base = declarative_base()

# Função utilitária para obter uma sessão do banco (para usar nas rotas/services)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()