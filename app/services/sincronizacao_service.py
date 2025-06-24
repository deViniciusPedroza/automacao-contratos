import os
import logging
import aiohttp
from sqlalchemy.orm import Session
from app.models.documento_assinatura import DocumentoAssinatura
from app.models.arquivo import Arquivo

AUTENTIQUE_API_URL = "https://api.autentique.com.br/v2/graphql"
AUTENTIQUE_TOKEN = os.getenv("AUTENTIQUE_TOKEN")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")

async def documento_existe_autentique(document_id: str) -> bool:
    query = """
    query {
      document(id: "%s") {
        id
      }
    }
    """ % document_id
    headers = {"Authorization": f"Bearer {AUTENTIQUE_TOKEN}"}
    async with aiohttp.ClientSession() as session:
        async with session.post(AUTENTIQUE_API_URL, json={"query": query}, headers=headers) as resp:
            data = await resp.json()
            return bool(data.get("data", {}).get("document"))

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

    # Sincronizar documentos do Autentique
    documentos = db.query(DocumentoAssinatura).all()
    for doc in documentos:
        existe = await documento_existe_autentique(doc.documento_id_autentique)
        if not existe:
            logging.info(f"Removendo do banco documento Autentique órfão: {doc.id} ({doc.documento_id_autentique})")
            db.delete(doc)
            removidos_autentique.append(doc.id)

    # Sincronizar arquivos do Cloudinary
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