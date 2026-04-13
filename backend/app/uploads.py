import mimetypes
import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

BACKEND_ROOT = Path(__file__).resolve().parents[1]
UPLOADS_DIR = BACKEND_ROOT / "uploads"
PRODUCT_UPLOADS_DIR = UPLOADS_DIR / "products"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}


def ensure_upload_directories() -> None:
    PRODUCT_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "product"


def save_product_image(
    upload: UploadFile,
    *,
    store_id: int,
    sku: str,
) -> str:
    ensure_upload_directories()

    if not upload.filename:
        raise HTTPException(status_code=400, detail="Image file is missing a filename")

    content_type = (upload.content_type or "").lower().strip()
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed")

    extension = Path(upload.filename).suffix.lower().strip()
    if not extension and content_type:
        extension = (mimetypes.guess_extension(content_type) or "").lower()
    if extension == ".jpe":
        extension = ".jpg"
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image format. Use jpg, png, webp, gif, heic, or heif.",
        )

    store_dir = PRODUCT_UPLOADS_DIR / f"store-{store_id}"
    store_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{_slugify(sku)}-{uuid4().hex}{extension}"
    destination = store_dir / filename

    upload.file.seek(0)
    with destination.open("wb") as output_file:
        shutil.copyfileobj(upload.file, output_file)

    return f"/uploads/products/store-{store_id}/{filename}"


def delete_uploaded_image(image_url: str | None) -> None:
    if not image_url or not image_url.startswith("/uploads/"):
        return

    candidate = (BACKEND_ROOT / image_url.lstrip("/")).resolve()
    uploads_root = UPLOADS_DIR.resolve()

    try:
        candidate.relative_to(uploads_root)
    except ValueError:
        return

    if candidate.is_file():
        candidate.unlink()
