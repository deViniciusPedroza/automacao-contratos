import cloudinary.uploader
from fastapi import UploadFile
from typing import Optional
import uuid
from sqlalchemy.orm import Session
from app.models.arquivo import Arquivo, TipoArquivo

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

async def upload_pdf_to_cloudinary(
    etapa: str,
    file: UploadFile,
    processo_id: int,
    db: Session,
    filename_override: Optional[str] = None
):
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
        overwrite=True,
        access_mode="public"  # <-- Torna o arquivo público!
    )

    url = upload_result.get("secure_url")
    cloudinary_id = upload_result.get("public_id")

    # Cria registro no banco
    arquivo = Arquivo(
        processo_id=processo_id,
        etapa=etapa,
        public_id=cloudinary_id,
        url=url,
        tipo=TipoArquivo.INDIVIDUAL
    )
    db.add(arquivo)
    db.commit()
    db.refresh(arquivo)

    return {
        "message": f"Upload para a pasta '{etapa}' realizado com sucesso.",
        "url": url,
        "cloudinary_id": cloudinary_id,
        "arquivo_id": arquivo.id
    }