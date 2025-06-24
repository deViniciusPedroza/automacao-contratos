import os
import hmac
import hashlib
import json
import logging
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.documento_assinatura import DocumentoAssinatura
from app.models.assinatura_signatario import AssinaturaSignatario
from app.models.processo import Processo

router = APIRouter(prefix="/webhook", tags=["Webhook"])

AUTENTIQUE_ENDPOINT_SECRET = os.getenv("AUTENTIQUE_ENDPOINT_SECRET")

def verificar_assinatura_hmac(raw_body: bytes, signature: str, secret: str) -> bool:
    """
    Valida a assinatura HMAC SHA256 do Autentique.
    """
    if not signature:
        return False
    calculated_signature = hmac.new(
        secret.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(calculated_signature, signature)

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

    # Validação da assinatura HMAC
    if not verificar_assinatura_hmac(raw_body, x_autentique_signature or "", AUTENTIQUE_ENDPOINT_SECRET):
        logging.warning("Tentativa de acesso ao webhook com assinatura HMAC inválida.")
        raise HTTPException(status_code=401, detail="Unauthorized webhook source.")

    logging.info(f"Webhook recebido do Autentique: {payload}")

    # --- Lógica de atualização de status ---
    try:
        event = payload.get("event", {})
        event_type = event.get("type", "")
        data = event.get("data", {})
        # O id do documento pode estar em diferentes lugares dependendo do tipo de evento
        document_id = data.get("document") or data.get("object", {}).get("document") or data.get("object", {}).get("id")
        if not document_id:
            logging.warning("ID do documento não encontrado no payload.")
            return {"ok": False, "erro": "ID do documento não encontrado."}

        # Busca o documento no banco
        doc = db.query(DocumentoAssinatura).filter_by(documento_id_autentique=document_id).first()
        if not doc:
            logging.warning(f"Documento com id_autentique {document_id} não encontrado no banco.")
            return {"ok": False, "erro": "Documento não encontrado."}

        # Identifica o e-mail do signatário que assinou
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

        # Atualiza o status do signatário, se possível
        if signatario_email:
            signatario = db.query(AssinaturaSignatario).filter_by(documento_assinatura_id=doc.id, email=signatario_email).first()
            if signatario and signatario.status_assinatura != "assinado":
                signatario.status_assinatura = "assinado"
                db.commit()
                logging.info(f"Status do signatário {signatario_email} atualizado para 'assinado'.")
        else:
            logging.warning("E-mail do signatário não encontrado no payload.")

        # Verifica se todos os signatários já assinaram
        signatarios = db.query(AssinaturaSignatario).filter_by(documento_assinatura_id=doc.id).all()
        if signatarios and all(s.status_assinatura == "assinado" for s in signatarios):
            if doc.status != "assinado":
                doc.status = "assinado"
                db.commit()
                logging.info(f"Documento {doc.id} atualizado para status 'assinado'.")
            # Atualiza o processo correspondente para AGUARDANDO_CTE (em maiúsculo)
            if hasattr(doc, "processo_id") and doc.processo_id:
                processo = db.query(Processo).filter_by(id=doc.processo_id).first()
                if processo and processo.status != "AGUARDANDO_CTE":
                    processo.status = "AGUARDANDO_CTE"
                    db.commit()
                    logging.info(f"Processo {processo.id} atualizado para status 'AGUARDANDO_CTE'.")

        return {"ok": True}
    except Exception as e:
        logging.exception("Erro ao processar webhook do Autentique")
        return {"ok": False, "erro": str(e)}