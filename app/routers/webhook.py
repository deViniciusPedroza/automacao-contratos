import os
import hmac
import hashlib
import json
import logging
import aiohttp
import asyncio
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends, UploadFile
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.documento_assinatura import DocumentoAssinatura
from app.models.assinatura_signatario import AssinaturaSignatario
from app.models.processo import Processo
from app.services.upload_service import upload_pdf_to_cloudinary, is_valid_folder
from io import BytesIO

router = APIRouter(prefix="/webhook", tags=["Webhook"])

AUTENTIQUE_ENDPOINT_SECRET = os.getenv("AUTENTIQUE_ENDPOINT_SECRET")
AUTENTIQUE_TOKEN = os.getenv("AUTENTIQUE_TOKEN")
AUTENTIQUE_API_URL = "https://api.autentique.com.br/v2/graphql"

def verificar_assinatura_hmac(raw_body: bytes, signature: str, secret: str) -> bool:
    if not signature:
        return False
    calculated_signature = hmac.new(
        secret.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(calculated_signature, signature)

async def buscar_documento_autentique_por_id(document_id: str, token: str):
    query = """
    query ($id: UUID!) {
      document(id: $id) {
        id
        name
        files {
          original
          signed
        }
      }
    }
    """
    variables = {"id": document_id}
    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            AUTENTIQUE_API_URL,
            json={"query": query, "variables": variables},
            headers=headers
        )
        status_code = resp.status
        data = await resp.json()
        return data, status_code

async def baixar_pdf_assinado(url: str, token: str) -> bytes:
    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise Exception(f"Erro ao baixar PDF assinado: {resp.status}")
            return await resp.read()

def criar_uploadfile_from_bytes(pdf_bytes: bytes, filename: str) -> UploadFile:
    upload_file = UploadFile(filename=filename, file=BytesIO(pdf_bytes))
    # Se seu upload_pdf_to_cloudinary precisar do content_type, descomente a linha abaixo:
    # upload_file.content_type = "application/pdf"
    return upload_file

@router.post("/autentique", status_code=status.HTTP_200_OK)
async def autentique_webhook(
    request: Request,
    x_autentique_signature: str = Header(None, alias="X-Autentique-Signature"),
    db: Session = Depends(get_db)
):
    if not AUTENTIQUE_ENDPOINT_SECRET:
        logging.error("AUTENTIQUE_ENDPOINT_SECRET não está definida nas variáveis de ambiente.")
        raise HTTPException(status_code=500, detail="Webhook secret não configurado no servidor.")

    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except Exception:
        logging.error("Payload do webhook não é um JSON válido.")
        raise HTTPException(status_code=400, detail="Payload inválido.")

    if not verificar_assinatura_hmac(raw_body, x_autentique_signature or "", AUTENTIQUE_ENDPOINT_SECRET):
        logging.warning("Tentativa de acesso ao webhook com assinatura HMAC inválida.")
        raise HTTPException(status_code=401, detail="Unauthorized webhook source.")

    logging.info(f"Webhook recebido do Autentique: {payload}")

    try:
        event = payload.get("event", {})
        event_type = event.get("type", "")
        data = event.get("data", {})
        document_id = data.get("document") or data.get("object", {}).get("document") or data.get("object", {}).get("id")
        if not document_id:
            logging.warning("ID do documento não encontrado no payload.")
            return {"ok": False, "erro": "ID do documento não encontrado."}

        doc = db.query(DocumentoAssinatura).filter_by(documento_id_autentique=document_id).first()
        if not doc:
            logging.warning(f"Documento com id_autentique {document_id} não encontrado no banco.")
            return {"ok": False, "erro": "Documento não encontrado."}

        signatario_email = None
        if "user" in data:
            signatario_email = data["user"].get("email")
        if not signatario_email and "events" in data:
            for ev in data["events"]:
                if ev.get("type") in ("signed", "signature.accepted"):
                    signatario_email = ev.get("user", {}).get("email")
                    break
        if not signatario_email and "object" in data and "signatures" in data["object"]:
            for sig in data["object"]["signatures"]:
                if sig.get("signed"):
                    signatario_email = sig.get("email")
                    break

        if signatario_email:
            signatario = db.query(AssinaturaSignatario).filter_by(documento_assinatura_id=doc.id, email=signatario_email).first()
            if signatario and signatario.status_assinatura != "assinado":
                signatario.status_assinatura = "assinado"
                db.commit()
                logging.info(f"Status do signatário {signatario_email} atualizado para 'assinado'.")
        else:
            logging.warning("E-mail do signatário não encontrado no payload.")

        signatarios = db.query(AssinaturaSignatario).filter_by(documento_assinatura_id=doc.id).all()
        if signatarios and all(s.status_assinatura == "assinado" for s in signatarios):
            if doc.status != "assinado":
                doc.status = "assinado"
                db.commit()
                logging.info(f"Documento {doc.id} atualizado para status 'assinado'.")
            if hasattr(doc, "processo_id") and doc.processo_id:
                processo = db.query(Processo).filter_by(id=doc.processo_id).first()
                if processo and processo.status != "AGUARDANDO_CTE":
                    processo.status = "AGUARDANDO_CTE"
                    db.commit()
                    logging.info(f"Processo {processo.id} atualizado para status 'AGUARDANDO_CTE'.")

            try:
                if not AUTENTIQUE_TOKEN:
                    logging.error("AUTENTIQUE_TOKEN não está definida nas variáveis de ambiente.")
                    raise Exception("AUTENTIQUE_TOKEN não configurado.")

                signed_url = None
                doc_autentique = None
                for tentativa in range(3):
                    data_autentique, status_code = await buscar_documento_autentique_por_id(doc.documento_id_autentique, AUTENTIQUE_TOKEN)
                    logging.info(f"Tentativa {tentativa+1}: Status HTTP={status_code}, Resposta Autentique={json.dumps(data_autentique)}")
                    doc_autentique = data_autentique.get("data", {}).get("document") if data_autentique else None
                    if doc_autentique and doc_autentique.get("files") and doc_autentique["files"].get("signed"):
                        signed_url = doc_autentique["files"]["signed"]
                        break
                    await asyncio.sleep(3)

                if signed_url:
                    pdf_bytes = await baixar_pdf_assinado(signed_url, AUTENTIQUE_TOKEN)
                    filename = f"{doc_autentique['name']}.pdf"
                    upload_file = criar_uploadfile_from_bytes(pdf_bytes, filename)
                    upload_result = await upload_pdf_to_cloudinary(
                        etapa="contratos",
                        file=upload_file,
                        processo_id=doc.processo_id,
                        db=db,
                        filename_override=doc_autentique["name"]
                    )
                    logging.info(f"Upload do PDF assinado para Cloudinary realizado com sucesso: {upload_result.get('url')}")
                else:
                    logging.warning("Arquivo assinado não encontrado no Autentique para upload após múltiplas tentativas.")
            except Exception as e:
                logging.exception(f"Erro ao buscar/upload PDF assinado do Autentique: {str(e)}")

        return {"ok": True}
    except Exception as e:
        logging.exception("Erro ao processar webhook do Autentique")
        return {"ok": False, "erro": str(e)}