"""
Image Generation Service (OpenAI DALL-E 3)
Generates photorealistic room renders from visualization prompts.
"""
import openai
from ..config import settings
from .storage import upload_render

openai.api_key = settings.openai_api_key


async def generate_room_render(
    prompt: str,
    project_id: str,
    room: str,
    style: str,
) -> str:
    """
    Generate a room render with DALL-E 3 and store it in Cloudinary.
    Returns the final Cloudinary URL.
    """
    client = openai.OpenAI(api_key=settings.openai_api_key)

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt[:4000],  # DALL-E 3 limit
        n=1,
        size="1792x1024",
        quality="hd",
        style="natural",
    )

    dalle_url = response.data[0].url
    cloudinary_url = upload_render(dalle_url, project_id, room, style)
    return cloudinary_url
