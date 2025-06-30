import os
import aiohttp
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.arquivo import Arquivo
from app.services.upload_service import upload_pdf_to_cloudinary
from io import BytesIO
from PyPDF2 import PdfMerger
import re

router = APIRouter(prefix="/agrupamento", tags=["Agrupamento de Arquivos"])

# Função para baixar um PDF a partir da URL
async def baixar_pdf(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Erro ao baixar PDF: {resp.status} - {url}")
            return await resp.read()

# Função para criar UploadFile a partir de bytes
def criar_uploadfile_from_bytes(pdf_bytes: bytes, filename: str) -> UploadFile:
    upload_file = UploadFile(filename=filename, file=BytesIO(pdf_bytes))
    # upload_file.content_type = "application/pdf"  # Opcional
    return upload_file

@router.post("/processo/{processo_id}/agrupar-e-upload")
async def agrupar_e_upload(
    processo_id: int,
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
        raise HTTPException(status_code=400, detail="Arquivo de contrato não encontrado.")

    # 2. Define os public_id obrigatórios (sem extensão) na ordem solicitada
    obrigatorios_em_ordem = [
        f"automacao-contratos/contratos/Contrato de Transporte - {numero_contrato}",                # Contrato de Transporte
        f"automacao-contratos/cte/{numero_contrato} - manifesto",                                   # manifesto
        f"automacao-contratos/raster/{numero_contrato} - raster_motorista",                         # raster_motorista
        f"automacao-contratos/raster/{numero_contrato} - raster_veiculo",                           # raster_veiculo
        f"automacao-contratos/rntrc/{numero_contrato} - rntrc",                                     # rntrc
        f"automacao-contratos/comprovantes/{numero_contrato} - comprovante",                        # comprovante
        f"automacao-contratos/cte/{numero_contrato} - cte",                                         # cte
    ]

    # 3. Monta um dicionário de arquivos encontrados (ignorando extensão)
    arquivos_sem_ext = {}
    for arq in arquivos:
        sem_ext = arq.public_id
        if sem_ext.endswith(".pdf"):
            sem_ext = sem_ext[:-4]
        arquivos_sem_ext[sem_ext] = arq

    # 4. Baixa os PDFs obrigatórios na ordem correta
    pdfs_bytes = []
    arquivos_na_ordem = []
    for pubid in obrigatorios_em_ordem:
        arq = arquivos_sem_ext.get(pubid)
        if not arq:
            raise HTTPException(status_code=400, detail=f"Arquivo obrigatório não encontrado: {pubid}")
        try:
            pdf_bytes = await baixar_pdf(arq.url)
            pdfs_bytes.append(pdf_bytes)
            arquivos_na_ordem.append(arq.public_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erro ao baixar {arq.public_id}: {str(e)}")

    # 5. Junta todos os PDFs em um só
    merger = PdfMerger()
    for pdf_bytes in pdfs_bytes:
        merger.append(BytesIO(pdf_bytes))
    output_buffer = BytesIO()
    merger.write(output_buffer)
    merger.close()
    output_buffer.seek(0)

    # 6. Cria UploadFile para enviar ao Cloudinary
    nome_agrupado = f"{numero_contrato} - agrupado.pdf"
    upload_file = criar_uploadfile_from_bytes(output_buffer.read(), nome_agrupado)

    # 7. Faz upload para Cloudinary (etapa 'agrupado')
    upload_result = await upload_pdf_to_cloudinary(
        etapa="agrupado",
        file=upload_file,
        processo_id=processo_id,
        db=db,
        filename_override=f"{numero_contrato} - agrupado"
    )

    return {
        "ok": True,
        "mensagem": "PDF agrupado criado e enviado ao Cloudinary com sucesso.",
        "public_id": upload_result.get("public_id"),
        "url": upload_result.get("url"),
        "arquivos_agrupados": arquivos_na_ordem
    }