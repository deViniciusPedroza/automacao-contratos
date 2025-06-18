from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from app.services.upload_service import upload_pdf_to_cloudinary, is_valid_folder
from app.database import get_db

router = APIRouter()

@router.post("/upload/{processo_id}/{etapa}")
async def upload_pdf(
    processo_id: int,
    etapa: str,
    file: UploadFile = File(...),
    filename: str = Query(default=None, description="Nome desejado para o arquivo (sem .pdf)"),
    db: Session = Depends(get_db)
):
    if not is_valid_folder(etapa):
        raise HTTPException(status_code=400, detail="Pasta de etapa inválida.")

    try:
        result = await upload_pdf_to_cloudinary(etapa, file, processo_id, db, filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao fazer upload: {str(e)}")