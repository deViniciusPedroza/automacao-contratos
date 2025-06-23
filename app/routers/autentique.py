from fastapi import APIRouter, HTTPException, status
from app.schemas.autentique import DocumentoAutentiqueInput, DocumentoAutentiqueOutput
from app.services.autentique_service import processar_documento_autentique

router = APIRouter(prefix="/autentique", tags=["Autentique"])

@router.post("/documento/", response_model=DocumentoAutentiqueOutput)
async def criar_documento_autentique(payload: DocumentoAutentiqueInput):
    """
    Cria um documento no Autentique, envia para assinatura e retorna os links de assinatura.
    
    Exemplo de payload:
    {
      "nome_documento": "Contrato de transporte - 56765",
      "arquivo_cloudinary": "https://res.cloudinary.com/dwddq88x2/raw/upload/v1750692371/automacao-contratos/contratos/56765.pdf",
      "cc_email": "vinicius.silva@raklog.com.br",
      "signers": [
        {
          "name": "Fulano",
          "email": "fulano@email.com",
          "positions": [
            {"x": "5.0", "y": "92.0", "z": 1, "element": "SIGNATURE"},
            {"x": "5.0", "y": "92.0", "z": 2, "element": "SIGNATURE"}
          ]
        }
      ]
    }
    """
    try:
        resultado = await processar_documento_autentique(payload)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))