from fastapi import APIRouter, UploadFile, File, HTTPException
import cloudinary.uploader
import os

router = APIRouter()

# Lista de pastas válidas
VALID_FOLDERS = [
    "raster",
    "rntrc",
    "contratos",
    "comprovantes",
    "cte",
    "agrupamento",
    "outros"
]

@router.post("/upload/{etapa}")
async def upload_pdf(etapa: str, file: UploadFile = File(...)):
    if etapa not in VALID_FOLDERS:
        raise HTTPException(status_code=400, detail="Pasta de etapa inválida.")

    try:
        result = cloudinary.uploader.upload(
            file.file,
            resource_type="raw",
            folder=f"automacao-contratos/{etapa}"
        )
        return {
            "message": f"Upload para a pasta '{etapa}' realizado com sucesso.",
            "url": result.get("secure_url")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao fazer upload: {str(e)}")
