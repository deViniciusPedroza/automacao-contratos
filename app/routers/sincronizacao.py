from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.sincronizacao_service import sincronizar_documentos

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/sincronizar-documentos", status_code=200)
async def sincronizar_documentos_endpoint(db: Session = Depends(get_db)):
    """
    Sincroniza os documentos do banco de dados com Autentique e Cloudinary.
    Remove registros órfãos do banco e retorna um relatório do que foi removido.
    """
    try:
        resultado = await sincronizar_documentos(db)
        return {"status": "ok", "detalhes": resultado}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))