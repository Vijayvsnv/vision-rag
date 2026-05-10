import base64
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_description(image_path: str) -> str:
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert image analysis assistant. Your job is to generate a rich, in-depth description of the image that will be used for semantic vector search. "
                    "Cover ALL of the following in your description:\n"
                    "- Scene overview: where is this, what is happening overall\n"
                    "- People: count, gender, approximate age, clothing colors and type, hair, body language, facial expressions, actions, positions (standing/sitting/walking)\n"
                    "- Objects: every visible object, its color, size, position in the frame\n"
                    "- Text: any visible text, signs, labels, timestamps, numbers — read them exactly\n"
                    "- Colors: dominant colors in the scene\n"
                    "- Background and foreground details: walls, floors, furniture, outdoor elements\n"
                    "- Lighting: bright, dark, artificial, natural\n"
                    "- Camera type: CCTV, phone camera, professional camera, etc. if determinable\n"
                    "Write as a single flowing paragraph. Be specific and detailed. "
                    "Return only the description as plain text, no JSON, no headers, no bullet points."
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                    }
                ]
            }
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content.strip()


def get_embedding(text: str) -> list:
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    return response.data[0].embedding
