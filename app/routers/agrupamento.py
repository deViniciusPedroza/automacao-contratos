from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.arquivo import Arquivo
import re

router = APIRouter(prefix="/verifica-arquivos", tags=["Verificação de Arquivos"])

@router.get("/agrupamento")
def verifica_arquivos_para_agrupamento(
    processo_id: int = Query(..., description="ID do processo"),
    db: Session = Depends(get_db)
):
    # Busca todos os arquivos do processo
    arquivos = db.query(Arquivo).filter(Arquivo.processo_id == processo_id).all()
    if not arquivos:
        raise HTTPException(status_code=404, detail="Nenhum arquivo encontrado para esse processo_id.")

    # 1. Encontra o arquivo de contrato e extrai o número
    contrato_pattern = r"automacao-contratos/contratos/Contrato de Transporte - (\d+)"
    numero_contrato = None
    for arq in arquivos:
        match = re.match(contrato_pattern, arq.public_id)
        if match:
            numero_contrato = match.group(1)
            break

    if not numero_contrato:
        return {
            "ok": False,
            "motivo": "Arquivo de contrato não encontrado.",
            "arquivos_encontrados": [arq.public_id for arq in arquivos]
        }

    # 2. Define os public_id obrigatórios
    obrigatorios = [
        f"automacao-contratos/contratos/Contrato de Transporte - {numero_contrato}",
        f"automacao-contratos/comprovantes/{numero_contrato} - comprovante",
        f"automacao-contratos/rntrc/{numero_contrato} - rntrc",
        f"automacao-contratos/raster/{numero_contrato} - raster_motorista",
        f"automacao-contratos/raster/{numero_contrato} - raster_veiculo",
        f"automacao-contratos/cte/{numero_contrato} - manifesto",
        f"automacao-contratos/cte/{numero_contrato} - cte",
    ]

    # 3. Monta um dicionário de arquivos encontrados (ignorando extensão)
    arquivos_sem_ext = set()
    for arq in arquivos:
        sem_ext = arq.public_id
        if sem_ext.endswith(".pdf"):
            sem_ext = sem_ext[:-4]
        arquivos_sem_ext.add(sem_ext)

    resultado = {}
    for pubid in obrigatorios:
        resultado[pubid] = pubid in arquivos_sem_ext

    return {
        "ok": all(resultado.values()),
        "numero_contrato": numero_contrato,
        "arquivos_obrigatorios": resultado,
        "arquivos_encontrados": [arq.public_id for arq in arquivos]
    }