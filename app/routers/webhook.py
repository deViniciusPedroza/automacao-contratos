import os
import logging
from fastapi import APIRouter, Request, Header, HTTPException, status

router = APIRouter(prefix="/webhook", tags=["Webhook"])

AUTENTIQUE_ENDPOINT_SECRET = os.getenv("AUTENTIQUE_ENDPOINT_SECRET")

@router.post("/autentique", status_code=status.HTTP_200_OK)
async def autentique_webhook(
    request: Request,
    x_endpoint_secret: str = Header(None, alias="X-Endpoint-Secret")
):
    # Validação do secret
    if not AUTENTIQUE_ENDPOINT_SECRET:
        logging.error("AUTENTIQUE_ENDPOINT_SECRET não está definida nas variáveis de ambiente.")
        raise HTTPException(status_code=500, detail="Webhook secret não configurado no servidor.")
    if x_endpoint_secret != AUTENTIQUE_ENDPOINT_SECRET:
        logging.warning("Tentativa de acesso ao webhook com secret inválido.")
        raise HTTPException(status_code=401, detail="Unauthorized webhook source.")

    payload = await request.json()
    logging.info(f"Webhook recebido do Autentique: {payload}")

    # Apenas retorna o JSON recebido
    return payload