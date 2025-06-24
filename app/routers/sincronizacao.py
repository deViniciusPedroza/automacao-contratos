from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.sincronizacao_service import sincronizar_documentos
import logging

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/sincronizar-documentos", status_code=200)
async def sincronizar_documentos_endpoint(db: Session = Depends(get_db)):
    try:
        logging.info("Iniciando sincronização de documentos com Autentique e Cloudinary.")
        resultado = await sincronizar_documentos(db)
        logging.info(f"Sincronização concluída. Detalhes: {resultado}")
        return {"status": "ok", "detalhes": resultado}
    except Exception as e:
        logging.exception("Erro ao sincronizar documentos.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))