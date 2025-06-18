import cloudinary
import cloudinary.api
from sqlalchemy.orm import Session
from app.models.arquivo import Arquivo

def list_files_by_folder(folder: str):
    """
    Lista arquivos na pasta especificada (prefixo do public_id).
    """
    response = cloudinary.api.resources(
        type="upload",
        resource_type="raw",
        prefix=f"automacao-contratos/{folder}/"
    )
    # Retorna lista de arquivos com public_id e url
    return [
        {
            "public_id": resource["public_id"],
            "url": resource["secure_url"]
        }
        for resource in response.get("resources", [])
    ]

def delete_file_by_public_id(public_id: str, db: Session):
    """
    Remove um arquivo do Cloudinary pelo public_id e remove do banco.
    """
    result = cloudinary.api.delete_resources(
        [public_id],
        resource_type="raw"
    )
    # Remove do banco se existir
    arquivo = db.query(Arquivo).filter(Arquivo.public_id == public_id).first()
    if arquivo:
        db.delete(arquivo)
        db.commit()
    return result