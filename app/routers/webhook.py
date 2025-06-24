import os
import hmac
import hashlib
import json
import logging
from fastapi import APIRouter, Request, Header, HTTPException, status

router = APIRouter(prefix="/webhook", tags=["Webhook"])

AUTENTIQUE_ENDPOINT_SECRET = os.getenv("AUTENTIQUE_ENDPOINT_SECRET")

def verify_signature(headers, payload, secret):
    signature = headers.get('x-autentique-signature')
    if not signature:
        return False
    payload_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    calculated_signature = hmac.new(secret.encode('utf-8'), payload_json, hashlib.sha256).hexdigest()
    return hmac.compare_digest(calculated_signature, signature)

@router.post("/autentique", status_code=status.HTTP_200_OK)
async def autentique_webhook(
    request: Request,
    x_autentique_signature: str = Header(None, alias="X-Autentique-Signature")
):
    if not AUTENTIQUE_ENDPOINT_SECRET:
        logging.error("AUTENTIQUE_ENDPOINT_SECRET não está definida nas variáveis de ambiente.")
        raise HTTPException(status_code=500, detail="Webhook secret não configurado no servidor.")

    # Recebe o corpo cru da requisição para garantir a assinatura correta
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except Exception:
        logging.error("Payload do webhook não é um JSON válido.")
        raise HTTPException(status_code=400, detail="Payload inválido.")

    # Calcula a assinatura HMAC
    calculated_signature = hmac.new(
        AUTENTIQUE_ENDPOINT_SECRET.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    # Valida a assinatura
    if not hmac.compare_digest(calculated_signature, x_autentique_signature or ""):
        logging.warning("Tentativa de acesso ao webhook com assinatura HMAC inválida.")
        raise HTTPException(status_code=401, detail="Unauthorized webhook source.")

    logging.info(f"Webhook recebido do Autentique: {payload}")

    # Apenas retorna o JSON recebido
    return payload