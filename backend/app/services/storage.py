import os
import requests
from typing import Tuple

# Servicio de Almacenamiento 100% Gratuito (Cloudinary / Fallback Local)
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_UPLOAD_PRESET = os.getenv("CLOUDINARY_UPLOAD_PRESET", "")  # Preset "unsigned" gratuito

def upload_image_to_free_cloud(file_bytes: bytes, filename: str) -> Tuple[str, str]:
    """
    Sube la fotografía a Cloudinary (100% gratis sin tarjeta) si hay credenciales configuradas.
    De lo contrario, guarda localmente en el servidor.
    """
    if CLOUDINARY_CLOUD_NAME and CLOUDINARY_UPLOAD_PRESET:
        try:
            url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"
            files = {"file": (filename, file_bytes, "image/jpeg")}
            data = {"upload_preset": CLOUDINARY_UPLOAD_PRESET}
            
            response = requests.post(url, files=files, data=data, timeout=15)
            if response.status_code == 200:
                res_data = response.json()
                secure_url = res_data.get("secure_url")
                public_id = res_data.get("public_id")
                return secure_url, public_id
        except Exception as e:
            print(f"Error al subir a Cloudinary: {e}")

    # Fallback local gratuito en el servidor
    os.makedirs("static/uploads", exist_ok=True)
    saved_path = os.path.join("static/uploads", filename)
    with open(saved_path, "wb") as f:
        f.write(file_bytes)
    
    return f"/static/uploads/{filename}", filename
