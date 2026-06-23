"""
Storage Service
Handles floor plan and render image uploads to AWS S3 and Cloudinary.
"""
import boto3
import cloudinary
import cloudinary.uploader
from io import BytesIO

from ..config import settings

# ── S3 client ─────────────────────────────────────────────────────────────────

_s3 = boto3.client(
    "s3",
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
)

# ── Cloudinary config ─────────────────────────────────────────────────────────

cloudinary.config(cloudinary_url=settings.cloudinary_url)


# ── Floor plans → S3 ─────────────────────────────────────────────────────────

def upload_floor_plan(
    file_bytes: bytes,
    filename: str,
    content_type: str = "image/jpeg",
) -> str:
    """Upload a floor plan image to S3. Returns the public URL."""
    key = f"floor-plans/{filename}"
    _s3.upload_fileobj(
        BytesIO(file_bytes),
        settings.aws_s3_bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return f"https://{settings.aws_s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"


def delete_floor_plan(filename: str):
    key = f"floor-plans/{filename}"
    _s3.delete_object(Bucket=settings.aws_s3_bucket, Key=key)


# ── Render images → Cloudinary ────────────────────────────────────────────────

def upload_render(image_url: str, project_id: str, room: str, style: str) -> str:
    """
    Upload a generated render image (from DALL-E URL) to Cloudinary.
    Returns the optimised Cloudinary URL.
    """
    result = cloudinary.uploader.upload(
        image_url,
        folder=f"interiorai/renders/{project_id}",
        public_id=f"{room.lower().replace(' ', '_')}_{style.lower()}",
        overwrite=True,
        resource_type="image",
        transformation=[
            {"width": 1920, "height": 1080, "crop": "fill", "quality": "auto"},
        ],
    )
    return result["secure_url"]


def upload_render_bytes(image_bytes: bytes, project_id: str, room: str, style: str) -> str:
    """Upload raw image bytes to Cloudinary."""
    result = cloudinary.uploader.upload(
        BytesIO(image_bytes),
        folder=f"interiorai/renders/{project_id}",
        public_id=f"{room.lower().replace(' ', '_')}_{style.lower()}",
        overwrite=True,
        resource_type="image",
    )
    return result["secure_url"]
