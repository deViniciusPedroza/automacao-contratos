import cloudinary.uploader
from fastapi import UploadFile
from typing import Optional
import uuid

VALID_FOLDERS = [
    "raster",
    "rntrc",
    "contratos",
    "comprovantes",
    "cte",
    "agrupamento",
    "outros"
]

def is_valid_folder(folder: str) -> bool:
    return folder in VALID_FOLDERS

async def upload_pdf_to_cloudinary(etapa: str, file: UploadFile, filename_override: Optional[str] = None):
    # Gera nome aleatório se não for informado
    if filename_override:
        public_id = f"automacao-contratos/{etapa}/{filename_override}"
    else:
        random_name = str(uuid.uuid4())
        public_id = f"automacao-contratos/{etapa}/{random_name}"

    upload_result = cloudinary.uploader.upload(
        file.file,
        resource_type="raw",
        public_id=public_id,
        format="pdf",  # Garante que seja PDF
        overwrite=True
    )

    return {
        "message": f"Upload para a pasta '{etapa}' realizado com sucesso.",
        "url": upload_result.get("secure_url"),
        "cloudinary_id": upload_result.get("public_id")
    }
