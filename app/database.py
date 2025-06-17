from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://raklog_postgresql_user:gl3oJ9qNd2XapCdq4h1hUWOQQy5x8OHB@dpg-d1883iogjchc73dsp830-a.ohio-postgres.render.com/raklog_postgresql"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
