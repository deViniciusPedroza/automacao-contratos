import cloudinary
import cloudinary.api

def list_files_by_folder(folder: str):
    """
    Lista arquivos na pasta especificada (prefixo do public_id).
    """
    response = cloudinary.api.resources(
        type="upload",
        resource_type="raw",
        prefix=f"automacao-contratos/{folder}/"
    )
    # Retorna lista de arquivos com public_id e url
    return [
        {
            "public_id": resource["public_id"],
            "url": resource["secure_url"]
        }
        for resource in response.get("resources", [])
    ]

def delete_file_by_public_id(public_id: str):
    """
    Remove um arquivo do Cloudinary pelo public_id.
    """
    result = cloudinary.api.delete_resources(
        [public_id],
        resource_type="raw"
    )
    return result