import base64
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_description(image_path: str, notes: str = None) -> str:
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    user_content = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
        }
    ]

    if notes and notes.strip():
        user_content.append({
            "type": "text",
            "text": f"Additional context: {notes}"
        })

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert security and surveillance officer with years of experience in threat detection, behavioral analysis, and public safety monitoring. Your job is to analyze images from a security perspective and identify any alarming, suspicious, or noteworthy activity.\n\n"
                    "For each image, provide a thorough security assessment covering ALL of the following:\n\n"
                    "- Threat level assessment: rate the scene as LOW / MEDIUM / HIGH risk and state why immediately\n"
                    "- Suspicious behavior: unusual body language, loitering, concealment, erratic movement, aggression, unauthorized access, or anything that deviates from expected norms\n"
                    "- Persons of interest: count, gender, approximate age, clothing (colors, type, any concealing garments like hoodies/masks/hats), body language, facial expressions, gaze direction, and actions\n"
                    "- Group dynamics: interactions between individuals — are they coordinating, following someone, acting as lookouts?\n"
                    "- Objects of concern: unattended bags, weapons, tools, vehicles out of place, or any item that could pose a risk\n"
                    "- Environmental context: location type (retail, transit, public space, restricted area), entry/exit points, blind spots, crowd density\n"
                    "- Text and identifiers: any visible license plates, ID badges, signage, timestamps, or labels — read them exactly\n"
                    "- Lighting and visibility: dark zones, obstructions, or conditions that could compromise security coverage\n"
                    "- Camera and coverage notes: camera type (CCTV, PTZ, body cam, etc.), angle, and any coverage gaps\n\n"
                    "Write your response as a structured security incident report. Lead with the threat level and the most critical observations first, followed by supporting details. Be direct, precise, and objective. Flag anything that warrants immediate escalation or follow-up action. Return plain text only — no JSON, no markdown headers, no bullet symbols."
                )
            },
            {
                "role": "user",
                "content": user_content
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
