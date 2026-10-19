import io
import wave
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
    spoken_reply: Optional[str] = None

class GeminiService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.text_model = "gemini-3.5-flash-lite"
        self.audio_model = "gemini-2.5-flash"
        self.tts_model = "gemini-2.5-flash-preview-tts"

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
            "Eres Lilo Hub, el asistente de IA personal de Renato. "
            "Escucha atentamente esta nota de voz. Realiza la transcripción exacta y organízala "
            "en una nota estructurada para Obsidian: título, resumen, tags y tareas.\n"
            "IMPORTANTE: En el campo 'spoken_reply', escribe una respuesta hablada, cercana, natural y concisa "
            "(máximo 2 a 3 oraciones en español) respondiendo directamente a lo que Renato preguntó o conversó, "
            "o confirmando afectuosamente lo que guardaste para él."
        )
        response = self.client.models.generate_content(
            model=self.audio_model,
            contents=[prompt, audio_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=StructuredNote,
                temperature=0.3
            )
        )
        return StructuredNote.model_validate_json(response.text)

    def generate_voice_audio(self, text: str) -> bytes:
        """Sintetiza texto a voz (TTS) con Gemini y devuelve bytes en formato WAV para Telegram."""
        response = self.client.models.generate_content(
            model=self.tts_model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"]
            )
        )
        pcm_data = response.candidates[0].content.parts[0].inline_data.data
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(pcm_data)
        return wav_io.getvalue()
