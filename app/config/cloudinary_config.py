import cloudinary
import os

# Pega a variável de ambiente
cloudinary_url = os.getenv("CLOUDINARY_URL")

# Configura o cloudinary usando a URL
cloudinary.config(
    secure=True,
    cloudinary_url=cloudinary_url
)
