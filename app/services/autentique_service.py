import os
import aiohttp
import tempfile
import logging
from typing import Dict
from app.schemas.autentique import DocumentoAutentiqueInput, DocumentoAutentiqueOutput, SignerOutput

logging.basicConfig(level=logging.INFO)

AUTENTIQUE_API_URL = "https://api.autentique.com.br/v2/graphql"
AUTENTIQUE_TOKEN = os.getenv("AUTENTIQUE_TOKEN")

async def baixar_arquivo_cloudinary(url_arquivo: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url_arquivo) as resp:
            if resp.status != 200:
                raise Exception(f"Erro ao baixar arquivo do Cloudinary: {resp.status}")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(await resp.read())
                return tmp.name  # <-- Isso deve ser uma string

async def enviar_mutation_autentique(query: str, variables: Dict, files: Dict = None):
    headers = {
        "Authorization": f"Bearer {AUTENTIQUE_TOKEN}"
    }
    data = {
        "query": query,
        "variables": variables
    }
    # Se for upload de arquivo, precisa multipart
    if files:
        form_data = aiohttp.FormData()
        form_data.add_field("operations", str(data).replace("'", '"'))
        map_dict = {str(i): f"variables.{k}" for i, k in enumerate(files.keys())}
        form_data.add_field("map", str(map_dict).replace("'", '"'))
        for i, (k, v) in enumerate(files.items()):
            if not isinstance(v, str):
                raise Exception(f"Esperado caminho do arquivo como string, recebido: {type(v)}")
            form_data.add_field(str(i), open(v, "rb"), filename=os.path.basename(v), content_type="application/pdf")
        async with aiohttp.ClientSession() as session:
            async with session.post(AUTENTIQUE_API_URL, data=form_data, headers=headers) as resp:
                return await resp.json()
    else:
        async with aiohttp.ClientSession() as session:
            async with session.post(AUTENTIQUE_API_URL, json=data, headers=headers) as resp:
                return await resp.json()

async def processar_documento_autentique(payload: DocumentoAutentiqueInput) -> DocumentoAutentiqueOutput:
    # 1. Baixar arquivo do Cloudinary usando a URL completa
    arquivo_local = await baixar_arquivo_cloudinary(payload.arquivo_cloudinary)
    logging.info("Arquivo baixado em:", arquivo_local, type(arquivo_local))

    # 2. Montar mutation de criação de documento
    create_document_mutation = """
    mutation CreateDocumentMutation($document: DocumentInput!, $signers: [SignerInput!]!, $file: Upload!) {
      createDocument(
        document: $document,
        signers: $signers,
        file: $file,
        folder_id: "ab6e826533f286d605477efead23ea44252a08f3"
      ) {
        id
        name
        signatures {
          public_id
          name
          email
        }
      }
    }
    """
    document_vars = {
        "document": {
            "name": payload.nome_documento,
            "refusable": True,
            "ignore_cpf": False,
            "stop_on_rejected": True,
            "configs": {
                "signature_appearance": "HANDWRITING",
                "lock_user_data": False
            },
            "cc": [{"email": payload.cc_email}]
        },
        "signers": [
            {
                "name": s.name,
                "email": s.email,
                "action": "SIGN",
                "positions": [p.dict() for p in s.positions]
            } for s in payload.signers
        ],
        "file": None  # Placeholder para upload
    }
    files = {"file": arquivo_local}

    # 3. Enviar mutation para criar documento
    resp = await enviar_mutation_autentique(create_document_mutation, document_vars, files)
    doc_data = resp["data"]["createDocument"]
    document_id = doc_data["id"]
    nome = doc_data["name"]
    signatures = doc_data["signatures"]

    # 4. Para cada signer, gerar link público de assinatura
    signer_outputs = []
    for sig in signatures:
        public_id = sig["public_id"]
        create_link_mutation = """
        mutation{
          createLinkToSignature(public_id: "%s"){
            short_link
          }
        }
        """ % public_id
        link_resp = await enviar_mutation_autentique(create_link_mutation, {})
        short_link = link_resp["data"]["createLinkToSignature"]["short_link"]
        signer_outputs.append(SignerOutput(
            public_id=public_id,
            name=sig["name"],
            email=sig["email"],
            link_assinatura=short_link
        ))

    # 5. Montar resposta
    return DocumentoAutentiqueOutput(
        document_id=document_id,
        nome=nome,
        signers=signer_outputs
    )