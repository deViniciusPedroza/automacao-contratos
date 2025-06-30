import os
import aiohttp
import asyncio
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.arquivo import Arquivo, TipoArquivo
from app.services.upload_service import upload_pdf_to_cloudinary
from app.services.cloudinary_file_service import delete_file_by_public_id
from io import BytesIO
from PyPDF2 import PdfMerger
import re

router = APIRouter(prefix="/agrupamento", tags=["Agrupamento de Arquivos"])

async def baixar_pdf(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Erro ao baixar PDF: {resp.status} - {url}")
            return await resp.read()

def criar_uploadfile_from_bytes(pdf_bytes: bytes, filename: str) -> UploadFile:
    upload_file = UploadFile(filename=filename, file=BytesIO(pdf_bytes))
    return upload_file

@router.post("/processo/{processo_id}/agrupar-e-upload")
async def agrupar_e_upload(
    processo_id: int,
    db: Session = Depends(get_db)
):
    arquivos = db.query(Arquivo).filter(Arquivo.processo_id == processo_id).all()
    if not arquivos:
        raise HTTPException(status_code=404, detail="Nenhum arquivo encontrado para esse processo_id.")

    contrato_pattern = r"automacao-contratos/contratos/Contrato de Transporte - (\d+)"
    numero_contrato = None
    for arq in arquivos:
        match = re.match(contrato_pattern, arq.public_id)
        if match:
            numero_contrato = match.group(1)
            break

    if not numero_contrato:
        raise HTTPException(status_code=400, detail="Arquivo de contrato não encontrado.")

    obrigatorios_em_ordem = [
        f"automacao-contratos/contratos/Contrato de Transporte - {numero_contrato}",                # Contrato de Transporte
        f"automacao-contratos/cte/{numero_contrato} - manifesto",                                   # manifesto
        f"automacao-contratos/raster/{numero_contrato} - raster_motorista",                         # raster_motorista
        f"automacao-contratos/raster/{numero_contrato} - raster_veiculo",                           # raster_veiculo
        f"automacao-contratos/rntrc/{numero_contrato} - rntrc",                                     # rntrc
        f"automacao-contratos/comprovantes/{numero_contrato} - comprovante",                        # comprovante
        f"automacao-contratos/cte/{numero_contrato} - cte",                                         # cte
    ]

    arquivos_sem_ext = {}
    for arq in arquivos:
        sem_ext = arq.public_id
        if sem_ext.endswith(".pdf"):
            sem_ext = sem_ext[:-4]
        arquivos_sem_ext[sem_ext] = arq

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

    merger = PdfMerger()
    for pdf_bytes in pdfs_bytes:
        merger.append(BytesIO(pdf_bytes))
    output_buffer = BytesIO()
    merger.write(output_buffer)
    merger.close()
    output_buffer.seek(0)

    nome_agrupado = f"{numero_contrato} - agrupado.pdf"
    upload_file = criar_uploadfile_from_bytes(output_buffer.read(), nome_agrupado)

    # Upload para Cloudinary na etapa 'agrupamento'
    upload_result = await upload_pdf_to_cloudinary(
        etapa="agrupamento",
        file=upload_file,
        processo_id=processo_id,
        db=db,
        filename_override=f"{numero_contrato} - agrupado"
    )

    # Atualiza o tipo do arquivo agrupado para AGRUPADO
    public_id_agrupado = upload_result.get("cloudinary_id")
    arquivo_agrupado = db.query(Arquivo).filter(
        Arquivo.processo_id == processo_id,
        Arquivo.public_id == public_id_agrupado
    ).first()
    if arquivo_agrupado:
        arquivo_agrupado.tipo = TipoArquivo.FINAL  # ou TipoArquivo.AGRUPADO se existir
        db.commit()

    # Remove arquivos INDIVIDUAL do Cloudinary e do banco
    arquivos_individuais = db.query(Arquivo).filter(
        Arquivo.processo_id == processo_id,
        Arquivo.tipo == TipoArquivo.INDIVIDUAL
    ).all()
    removidos = []
    for arq in arquivos_individuais:
        try:
            delete_file_by_public_id(arq.public_id, db)  # Agora passa o db correto!
            removidos.append(arq.public_id)
        except Exception as e:
            removidos.append(f"Erro ao remover {arq.public_id}: {str(e)}")

    return {
        "ok": True,
        "mensagem": "PDF agrupado criado, enviado ao Cloudinary, marcado como FINAL e arquivos INDIVIDUAL removidos do Cloudinary.",
        "public_id_agrupado": public_id_agrupado,
        "url_agrupado": upload_result.get("url"),
        "arquivos_agrupados": arquivos_na_ordem,
        "arquivos_individuais_removidos_cloudinary": removidos
    }