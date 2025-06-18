from sqlalchemy.orm import Session
from app.models.processo import Processo

def criar_processo(db: Session, nome: str, numero_contrato: str):
    processo = Processo(nome=nome, numero_contrato=numero_contrato)
    db.add(processo)
    db.commit()
    db.refresh(processo)
    return processo

def listar_processos(db: Session):
    return db.query(Processo).all()

def buscar_processo_por_numero(db: Session, numero_contrato: str):
    return db.query(Processo).filter(Processo.numero_contrato == numero_contrato).first()