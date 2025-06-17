from fastapi import APIRouter, UploadFile, File, HTTPException
import cloudinary.uploader
from app.config import cloudinary_config  # ativa configuração

router = APIRouter()

@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são permitidos.")

    result = cloudinary.uploader.upload(
        file.file,
        resource_type="raw",  # "raw" para PDFs e arquivos não-imagem
        folder="documentos"   # opcional: pasta onde armazenar
    )

    return {
        "url": result["secure_url"],
        "public_id": result["public_id"]
    }
