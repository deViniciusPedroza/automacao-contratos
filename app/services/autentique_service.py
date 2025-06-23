import os
import aiohttp
import tempfile
import logging
import json
import datetime
from typing import Dict
from app.schemas.autentique import DocumentoAutentiqueInput, DocumentoAutentiqueOutput, SignerOutput
from sqlalchemy.orm import Session
from app.models.processo import Processo, StatusProcesso
from app.models.documento_assinatura import DocumentoAssinatura
from app.models.assinatura_signatario import AssinaturaSignatario
from app.schemas.autentique import DocumentoAutentiqueInput, DocumentoAutentiqueOutput, SignerOutput

logging.basicConfig(level=logging.INFO)

AUTENTIQUE_API_URL = "https://api.autentique.com.br/v2/graphql"
AUTENTIQUE_TOKEN = os.getenv("AUTENTIQUE_TOKEN")

async def baixar_arquivo_cloudinary(url_arquivo: str) -> str:
    logging.info(f"Iniciando download do arquivo do Cloudinary: {url_arquivo}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url_arquivo) as resp:
            if resp.status != 200:
                logging.error(f"Erro ao baixar arquivo do Cloudinary: status {resp.status}")
                raise Exception(f"Erro ao baixar arquivo do Cloudinary: {resp.status}")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                content = await resp.read()
                tmp.write(content)
                logging.info(f"Arquivo baixado e salvo temporariamente em: {tmp.name} (tamanho: {len(content)} bytes)")
                return tmp.name

async def enviar_mutation_autentique(query: str, variables: Dict, files: Dict = None):
    headers = {
        "Authorization": f"Bearer {AUTENTIQUE_TOKEN}"
    }
    data = {
        "query": query,
        "variables": variables
    }
    if files:
        form_data = aiohttp.FormData()
        form_data.add_field("operations", json.dumps(data))
        map_dict = {str(i): [f"variables.{k}"] for i, k in enumerate(files.keys())}
        form_data.add_field("map", json.dumps(map_dict))
        for i, (k, v) in enumerate(files.items()):
            if not isinstance(v, str):
                logging.error(f"Esperado caminho do arquivo como string, recebido: {type(v)}")
                raise Exception(f"Esperado caminho do arquivo como string, recebido: {type(v)}")
            logging.info(f"Adicionando arquivo ao form-data: {v}")
            form_data.add_field(str(i), open(v, "rb"), filename=os.path.basename(v), content_type="application/pdf")
        async with aiohttp.ClientSession() as session:
            async with session.post(AUTENTIQUE_API_URL, data=form_data, headers=headers) as resp:
                resp_json = await resp.json()
                logging.info(f"Resposta da mutation (multipart): {resp_json}")
                return resp_json
    else:
        async with aiohttp.ClientSession() as session:
            async with session.post(AUTENTIQUE_API_URL, json=data, headers=headers) as resp:
                resp_json = await resp.json()
                logging.info(f"Resposta da mutation (json): {resp_json}")
                return resp_json

async def processar_documento_autentique_e_salvar(payload: DocumentoAutentiqueInput, db: Session) -> DocumentoAutentiqueOutput:
    # 1. Baixar o arquivo do Cloudinary
    arquivo_local = await baixar_arquivo_cloudinary(payload.arquivo_cloudinary)
    logging.info(f"Arquivo baixado em: {arquivo_local}")

    # 2. Montar a mutation e enviar para o Autentique
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
        "file": None
    }
    files = {"file": arquivo_local}

    resp = await enviar_mutation_autentique(create_document_mutation, document_vars, files)
    logging.info(f"Resposta da mutation createDocument: {resp}")

    if not resp or "data" not in resp or not resp["data"].get("createDocument"):
        logging.error(f"Resposta inesperada da API do Autentique: {resp}")
        raise Exception(f"Resposta inesperada da API do Autentique: {resp}")

    doc_data = resp["data"]["createDocument"]
    document_id = doc_data["id"]
    nome = doc_data["name"]
    signatures = doc_data["signatures"]

    # 3. Buscar o processo pelo numero_contrato (que é o nome do arquivo)
    # Extrai o número do contrato do nome do arquivo (ex: "56765.pdf" -> "56765")
    nome_arquivo = os.path.basename(payload.arquivo_cloudinary)
    numero_contrato = os.path.splitext(nome_arquivo)[0]

    processo = db.query(Processo).filter(Processo.numero_contrato == numero_contrato).first()
    if not processo:
        raise Exception(f"Processo não encontrado para o número de contrato: {numero_contrato}")

    # 4. Persistir DocumentoAssinatura
    documento_assinatura = DocumentoAssinatura(
        processo_id=processo.id,
        documento_id_autentique=document_id,
        nome_documento=nome,
        status="aguardando_assinatura",
        data_upload=datetime.datetime.utcnow()
    )
    db.add(documento_assinatura)
    db.flush()  # Para obter o ID do documento_assinatura

    signer_outputs = []
    for sig in signatures:
        public_id = sig["public_id"]
        name = sig.get("name")
        email = sig.get("email")
        # Só gera link para quem tem nome preenchido
        if name and name.strip():
            create_link_mutation = f"""
            mutation{{
              createLinkToSignature(public_id: "{public_id}"){{
                short_link
              }}
            }}
            """
            link_resp = await enviar_mutation_autentique(create_link_mutation, {})
            logging.info(f"Resposta da mutation createLinkToSignature para {public_id}: {link_resp}")
            short_link = None
            if link_resp and "data" in link_resp and link_resp["data"].get("createLinkToSignature"):
                short_link = link_resp["data"]["createLinkToSignature"].get("short_link")
            else:
                logging.warning(f"Não foi possível gerar link de assinatura para {public_id}: {link_resp.get('errors') if link_resp else 'Resposta vazia'}")
        else:
            short_link = None

        # 5. Persistir AssinaturaSignatario
        assinatura = AssinaturaSignatario(
            documento_assinatura_id=documento_assinatura.id,
            nome=name,
            email=email,
            telefone=None,  # Preencha se tiver no payload
            email_secundario=None,  # Preencha se tiver no payload
            link_assinatura=short_link,
            tipo_acesso="email",  # Ou outro tipo se disponível
            status_assinatura="aguardando",
            data_assinatura=None
        )
        db.add(assinatura)

        signer_outputs.append(SignerOutput(
            public_id=public_id,
            name=name,
            email=email,
            link_assinatura=short_link
        ))

    # 6. Atualizar status do processo
    processo.status = StatusProcesso.AGUARDANDO_ASSINATURA_CONTRATO
    db.commit()

    return DocumentoAutentiqueOutput(
        document_id=document_id,
        nome=nome,
        signers=signer_outputs
    )