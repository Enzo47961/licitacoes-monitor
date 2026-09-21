"""Configuração de conexão e sessão do banco de dados SQLite via SQLAlchemy."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'licitacoes.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Cria todas as tabelas registradas nos modelos, caso não existam."""
    from models import models  # noqa: F401 garante que os modelos sejam registrados
    Base.metadata.create_all(bind=engine)


def get_session():
    """Retorna uma nova sessão de banco de dados."""
    return SessionLocal()
