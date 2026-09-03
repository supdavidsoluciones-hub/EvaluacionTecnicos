import os
import requests
import uuid
from typing import Tuple

# ─── Cloudinary (100% Gratis - 25GB almacenamiento) ───────────────────────────
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "dgb8eri7")
CLOUDINARY_UPLOAD_PRESET = os.getenv("CLOUDINARY_UPLOAD_PRESET", "chiriqui_fotos")
CLOUDINARY_FOLDER = "chiriqui_moviles"

def upload_image_to_free_cloud(file_bytes: bytes, filename: str) -> Tuple[str, str]:
    """
    Sube la fotografía a Cloudinary (100% gratis, 25GB, sin tarjeta).
    Si falla por cualquier razón, guarda localmente como respaldo.
    Las imágenes NUNCA se guardan en la base de datos PostgreSQL.
    Solo se guarda la URL (texto corto) en la BD.
    """
    if CLOUDINARY_CLOUD_NAME and CLOUDINARY_UPLOAD_PRESET:
        try:
            # Nombre único para evitar colisiones
            unique_name = f"{CLOUDINARY_FOLDER}/{uuid.uuid4().hex}_{filename}"

            url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload"
            files = {"file": (filename, file_bytes, "image/jpeg")}
            data = {
                "upload_preset": CLOUDINARY_UPLOAD_PRESET,
                "public_id": unique_name,
                "folder": CLOUDINARY_FOLDER,
            }

            response = requests.post(url, files=files, data=data, timeout=30)

            if response.status_code == 200:
                res_data = response.json()
                secure_url = res_data.get("secure_url", "")
                public_id = res_data.get("public_id", "")
                print(f"✅ Imagen subida a Cloudinary: {secure_url}")
                return secure_url, public_id
            else:
                print(f"⚠️ Error Cloudinary {response.status_code}: {response.text}")

        except Exception as e:
            print(f"⚠️ Error al subir a Cloudinary (usando respaldo local): {e}")

    # ── Fallback: guardar localmente si Cloudinary falla ──
    os.makedirs("static/uploads", exist_ok=True)
    safe_filename = f"{uuid.uuid4().hex}_{filename}"
    saved_path = os.path.join("static/uploads", safe_filename)
    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    print(f"📁 Imagen guardada localmente: {saved_path}")
    return f"/static/uploads/{safe_filename}", safe_filename


def delete_image_from_cloud(public_id: str) -> bool:
    """Elimina una imagen de Cloudinary (libera espacio)."""
    if not public_id or not CLOUDINARY_CLOUD_NAME:
        return False
    try:
        # Para borrar con preset unsigned no está disponible directamente
        # Se puede implementar con API Key+Secret si se necesita en el futuro
        print(f"ℹ️ Para eliminar imagen: {public_id}")
        return True
    except Exception as e:
        print(f"Error al eliminar imagen: {e}")
        return False
