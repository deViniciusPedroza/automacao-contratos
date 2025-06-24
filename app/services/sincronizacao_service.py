import os
import logging
import aiohttp
from sqlalchemy.orm import Session
from app.models.documento_assinatura import DocumentoAssinatura
from app.models.arquivo import Arquivo

AUTENTIQUE_API_URL = "https://api.autentique.com.br/v2/graphql"
AUTENTIQUE_TOKEN = os.getenv("AUTENTIQUE_TOKEN")
AUTENTIQUE_FOLDER_ID = os.getenv("AUTENTIQUE_FOLDER_ID")  # Defina essa variável de ambiente com o ID da pasta correta
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")

async def listar_documentos_autentique(folder_id: str, limit: int = 60, page: int = 1):
    query = f"""
    query {{
      documentsByFolder(folder_id: "{folder_id}", limit: {limit}, page: {page}) {{
        total
        data {{
          id
          name
          created_at
        }}
      }}
    }}
    """
    headers = {"Authorization": f"Bearer {AUTENTIQUE_TOKEN}"}
    async with aiohttp.ClientSession() as session:
        async with session.post(AUTENTIQUE_API_URL, json={"query": query}, headers=headers) as resp:
            data = await resp.json()
            return data.get("data", {}).get("documentsByFolder", {}).get("data", [])

async def arquivo_existe_cloudinary(public_id: str) -> bool:
    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/resources/raw/upload"
    params = {"public_ids[]": public_id}
    auth = aiohttp.BasicAuth(CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET)
    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return False
            data = await resp.json()
            return bool(data.get("resources"))

async def sincronizar_documentos(db: Session):
    removidos_autentique = []
    removidos_cloudinary = []

    # 1. Buscar todos os documentos da pasta no Autentique (paginando se necessário)
    autentique_ids = set()
    page = 1
    while True:
        documentos_autentique = await listar_documentos_autentique(AUTENTIQUE_FOLDER_ID, limit=60, page=page)
        if not documentos_autentique:
            break
        autentique_ids.update(doc["id"] for doc in documentos_autentique)
        if len(documentos_autentique) < 60:
            break
        page += 1

    # 2. Buscar todos os documentos do banco e remover os órfãos
    documentos = db.query(DocumentoAssinatura).all()
    for doc in documentos:
        if doc.documento_id_autentique not in autentique_ids:
            logging.info(f"Removendo do banco documento Autentique órfão: {doc.id} ({doc.documento_id_autentique})")
            db.delete(doc)
            removidos_autentique.append(doc.id)

    # 3. Sincronizar arquivos do Cloudinary
    arquivos = db.query(Arquivo).all()
    for arq in arquivos:
        existe = await arquivo_existe_cloudinary(arq.public_id)
        if not existe:
            logging.info(f"Removendo do banco arquivo Cloudinary órfão: {arq.id} ({arq.public_id})")
            db.delete(arq)
            removidos_cloudinary.append(arq.id)

    db.commit()
    return {
        "removidos_autentique": removidos_autentique,
        "removidos_cloudinary": removidos_cloudinary
    }