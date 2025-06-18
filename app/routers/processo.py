from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.processo_service import criar_processo, listar_processos, buscar_processo_por_numero

router = APIRouter()

@router.post("/processos/")
def criar_processo_endpoint(nome: str, numero_contrato: str, db: Session = Depends(get_db)):
    processo = criar_processo(db, nome, numero_contrato)
    return {
        "processo_id": processo.id,
        "nome": processo.nome,
        "numero_contrato": processo.numero_contrato
    }

@router.get("/processos/")
def listar_processos_endpoint(db: Session = Depends(get_db)):
    processos = listar_processos(db)
    return [
        {
            "processo_id": p.id,
            "nome": p.nome,
            "numero_contrato": p.numero_contrato
        }
        for p in processos
    ]

@router.get("/processos/{numero_contrato}")
def buscar_processo_endpoint(numero_contrato: str, db: Session = Depends(get_db)):
    processo = buscar_processo_por_numero(db, numero_contrato)
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado.")
    return {
        "processo_id": processo.id,
        "nome": processo.nome,
        "numero_contrato": processo.numero_contrato
    }