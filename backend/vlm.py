# vlm.py

import base64
import json
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_image_description(image_path: str) -> dict:
    """Takes an image path and returns description + tags via GPT-4o Vision."""

    with open(image_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": """Analyze this image in detail. Return a JSON with exactly these fields:
                        {
                            "description": "detailed description of everything in the image",
                            "tags": ["tag1", "tag2", "tag3"]
                        }
                        Only return JSON, nothing else."""
                    }
                ]
            }
        ],
        max_tokens=500
    )

    result = response.choices[0].message.content
    # strip ```json wrapper if present
    result = result.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(result)
