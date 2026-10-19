import json
from typing import Optional
from pydantic import BaseModel
from google import genai
from google.genai import types
from src.config import settings

class StructuredNote(BaseModel):
    title: str
    summary: str
    tags: list[str]
    tasks: list[str]
    content_markdown: str
    transcription: Optional[str] = None

class GeminiService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # Model Tiering: Usamos modelos ultra ligeros y económicos para texto,
        # y modelos multimodales estándar para procesamiento de audio.
        self.text_model = "gemini-3.5-flash-lite"
        self.audio_model = "gemini-2.5-flash"

    def process_text(self, text: str) -> StructuredNote:
        prompt = (
            "Eres el asistente personal de Renato para su bóveda de Obsidian. "
            "Analiza el siguiente pensamiento, nota o tarea enviada desde Telegram. "
            "Genera un título conciso y limpio para el archivo, un resumen de 1-2 oraciones, "
            "etiquetas relevantes en minúsculas (sin #), una lista de tareas de acción si aplican, "
            "y el contenido formateado en Markdown claro y bien estructurado.\n\n"
            f"Texto del usuario:\n{text}"
        )
        try:
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=StructuredNote,
                    temperature=0.2
                )
            )
        except Exception:
            # Fallback en caso de indisponibilidad temporal de flash-lite
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=StructuredNote,
                    temperature=0.2
                )
            )
        return StructuredNote.model_validate_json(response.text)

    def process_audio(self, audio_bytes: bytes, mime_type: str = "audio/ogg") -> StructuredNote:
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        prompt = (
            "Eres el asistente personal de Renato para su bóveda de Obsidian. "
            "Escucha atentamente esta nota de voz. Realiza la transcripción exacta y luego "
            "organízala en una nota estructurada: título conciso para el archivo, resumen, "
            "etiquetas en minúsculas, tareas pendientes si se mencionan, y el cuerpo en Markdown claro."
        )
        response = self.client.models.generate_content(
            model=self.audio_model,
            contents=[prompt, audio_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=StructuredNote,
                temperature=0.2
            )
        )
        return StructuredNote.model_validate_json(response.text)
