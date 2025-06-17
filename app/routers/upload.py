from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from services.upload_service import upload_pdf_to_cloudinary, is_valid_folder

router = APIRouter()

@router.post("/upload/{etapa}")
async def upload_pdf(
    etapa: str,
    file: UploadFile = File(...),
    filename: str = Query(default=None, description="Nome desejado para o arquivo (sem .pdf)")
):
    if not is_valid_folder(etapa):
        raise HTTPException(status_code=400, detail="Pasta de etapa inválida.")

    try:
        result = await upload_pdf_to_cloudinary(etapa, file, filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao fazer upload: {str(e)}")
