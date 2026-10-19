import io
import wave
from typing import Optional, Tuple
from pydantic import BaseModel
from google import genai
from google.genai import types
from src.config import settings
from src.services.token_service import TokenService

class StructuredNote(BaseModel):
    title: str
    summary: str
    tags: list[str]
    tasks: list[str]
    content_markdown: str
    transcription: Optional[str] = None
    is_conversational: bool = False
    spoken_reply: Optional[str] = None

class GeminiService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.text_model = "gemini-3.5-flash-lite"
        self.audio_model = "gemini-2.5-flash"
        self.pro_model = "gemini-2.5-pro"
        self.tts_model = "gemini-2.5-flash-preview-tts"

    async def _log_tokens(self, user_id: int, model: str, feature: str, response):
        """Extrae el uso de tokens de la respuesta de Gemini y lo registra."""
        try:
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                meta = response.usage_metadata
                prompt = getattr(meta, "prompt_token_count", 0) or 0
                completion = getattr(meta, "candidates_token_count", 0) or 0
                total = getattr(meta, "total_token_count", 0) or (prompt + completion)
                await TokenService.log_usage(
                    user_id=user_id,
                    model_name=model,
                    feature=feature,
                    prompt_tokens=prompt,
                    completion_tokens=completion,
                    total_tokens=total
                )
        except Exception as e:
            print(f"Error registrando tokens: {e}")

    async def process_text(self, text: str, user_id: int = 0) -> StructuredNote:
        prompt = (
            "Eres el asistente personal de Renato para su bóveda de Obsidian. "
            "Analiza el siguiente pensamiento, nota o tarea enviada desde Telegram. "
            "Genera un título conciso y limpio para el archivo, un resumen de 1-2 oraciones, "
            "etiquetas relevantes en minúsculas (sin #), una lista de tareas de acción si aplican, "
            "y el contenido formateado en Markdown claro y bien estructurado.\n\n"
            f"Texto del usuario:\n{text}"
        )
        used_model = self.text_model
        try:
            response = self.client.models.generate_content(
                model=used_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=StructuredNote,
                    temperature=0.2
                )
            )
        except Exception:
            used_model = self.audio_model
            response = self.client.models.generate_content(
                model=used_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=StructuredNote,
                    temperature=0.2
                )
            )

        await self._log_tokens(user_id, used_model, "inbox_text", response)
        return StructuredNote.model_validate_json(response.text)

    async def process_audio(self, audio_bytes: bytes, mime_type: str = "audio/ogg", user_id: int = 0) -> StructuredNote:
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        prompt = (
            "Eres Lilo Hub, el asistente de IA personal de Renato. "
            "Escucha atentamente esta nota de voz. Realiza la transcripción exacta y organízala "
            "en una nota estructurada para Obsidian: título, resumen, tags y tareas.\n\n"
            "DISCRIMINACIÓN DE INTENCIÓN DE VOZ:\n"
            "- Si Renato está dictando una nota, tarea, pensamiento o recordatorio (ej: 'anota esto', 'segunda prueba...', 'comprar cables'), "
            "'is_conversational' DEBE SER FALSE y 'spoken_reply' DEBE SER NULL.\n"
            "- ÚNICAMENTE si Renato hace una pregunta explícita a la IA (ej: '¿cómo estás?', 'explícame tal concepto', 'respóndeme'), "
            "o entabla conversación directa esperando respuesta hablada, 'is_conversational' será TRUE y redactarás en 'spoken_reply' "
            "una respuesta amena, concisa y natural (máximo 2 oraciones en español)."
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
        await self._log_tokens(user_id, self.audio_model, "inbox_voice", response)
        return StructuredNote.model_validate_json(response.text)

    async def generate_voice_audio(self, text: str, user_id: int = 0) -> bytes:
        """Sintetiza texto a voz (TTS) con Gemini y devuelve bytes en formato WAV para Telegram."""
        response = self.client.models.generate_content(
            model=self.tts_model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"]
            )
        )
        await self._log_tokens(user_id, self.tts_model, "tts_voice_reply", response)

        pcm_data = response.candidates[0].content.parts[0].inline_data.data
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(pcm_data)
        return wav_io.getvalue()

    async def query_pro_model(self, query: str, user_id: int = 0) -> str:
        """Invoca Gemini 2.5 Pro para razonamiento analítico avanzado, código o estudio."""
        prompt = (
            "Eres Lilo Hub en Modo Pro (Gemini 2.5 Pro). Actúas como el consultor y tutor experto de Renato. "
            "Brinda una respuesta profunda, rigurosa, clara y estructurada en Markdown.\n\n"
            f"Consulta de Renato:\n{query}"
        )
        response = self.client.models.generate_content(
            model=self.pro_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3
            )
        )
        await self._log_tokens(user_id, self.pro_model, "pro_reasoning", response)
        return response.text
