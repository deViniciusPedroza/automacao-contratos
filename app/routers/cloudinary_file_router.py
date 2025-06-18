from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from app.services.cloudinary_file_service import list_files_by_folder, delete_file_by_public_id
from app.database import get_db

router = APIRouter()

@router.get("/files/{folder}")
def list_files(folder: str):
    """
    Lista arquivos de uma pasta específica no Cloudinary.
    """
    try:
        files = list_files_by_folder(folder)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar arquivos: {str(e)}")

@router.delete("/files")
def delete_file(
    public_id: str = Query(..., description="Public ID completo do arquivo a ser removido"),
    db: Session = Depends(get_db)
):
    """
    Remove um arquivo do Cloudinary e do banco pelo public_id.
    """
    try:
        result = delete_file_by_public_id(public_id, db)
        if result.get("deleted", {}).get(public_id) == "deleted":
            return {"message": "Arquivo removido do Cloudinary e do banco de dados."}
        else:
            return {"message": "Arquivo não encontrado ou já removido.", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao remover arquivo: {str(e)}")