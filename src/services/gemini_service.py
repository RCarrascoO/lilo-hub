import io
import wave
from typing import Optional, List
from pydantic import BaseModel
from google import genai
from google.genai import types
from src.config import settings
from src.services.token_service import TokenService
from src.services.system_service import SystemService
from src.services.wol_service import WOLService
from src.services.conversation_service import ConversationService

class StructuredResponse(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = []
    tasks: List[str] = []
    content_markdown: Optional[str] = None
    transcription: Optional[str] = None
    is_conversational: bool = False
    save_to_vault: bool = True
    spoken_reply: Optional[str] = None
    text_reply: Optional[str] = None

class GeminiService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.text_model = "gemini-3.5-flash-lite"
        self.audio_model = "gemini-2.5-flash"
        self.pro_model = "gemini-2.5-pro"
        self.tts_model = "gemini-2.5-flash-preview-tts"

    async def _log_tokens(self, user_id: int, model: str, feature: str, response):
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

    def _get_live_server_context(self) -> str:
        """Obtiene una cadena resumida del estado del servidor para inyectar si se consulta."""
        try:
            m = SystemService.get_metrics()
            ram = m["ram"]
            containers_str = ", ".join([f"{c['name']} ({c['status']})" for c in m["containers"]])
            return (
                f"ESTADO DEL SERVIDOR SANEHOST EN VIVO:\n"
                f"- CPU: {m['cpu_percent']}% ({m['cpu_count']} cores)\n"
                f"- RAM: {ram['used_gb']} GB usados de {ram['total_gb']} GB ({ram['percent']}%), libres: {ram['free_gb']} GB\n"
                f"- Discos: {m['disks'][0]['used_gb']} GB usados de {m['disks'][0]['total_gb']} GB ({m['disks'][0]['free_gb']} GB libres)\n"
                f"- Contenedores Docker activos: {containers_str}"
            )
        except Exception as e:
            return f"Estado del servidor: Error consultando metricas: {e}"

    async def process_message(
        self,
        text: Optional[str] = None,
        audio_bytes: Optional[bytes] = None,
        mime_type: str = "audio/ogg",
        user_id: int = 0
    ) -> StructuredResponse:
        """Procesa texto o audio manteniendo memoria de conversación e inyectando telemetría y contexto en vivo."""

        # 1. Recuperar historial reciente
        recent_history = await ConversationService.get_recent_history(user_id=user_id, limit=6)

        # 2. Contexto de herramientas en vivo
        server_ctx = self._get_live_server_context()

        system_instruction = (
            "Eres Lilo Hub, el orquestador y asistente personal de Renato. Tienes acceso directo a su servidor y a su bóveda de Obsidian.\n\n"
            f"{server_ctx}\n\n"
            "INSTRUCCIONES CLAVE:\n"
            "1. DISCRIMINACIÓN DE INTENCIÓN:\n"
            "   - SI EL USUARIO PIDE DATOS DEL SERVIDOR (CPU, RAM, Docker, estado): Usa los datos en vivo provistos arriba. Responde con precisión en 'text_reply' y si es audio también en 'spoken_reply'. Pon 'save_to_vault: false' (NO guardes notas en Obsidian de consultas del servidor).\n"
            "   - SI EL USUARIO PIDE ENCENDER SU PC: Confírmale que enviarás el paquete Wake-on-LAN. Pon 'save_to_vault: false'.\n"
            "   - SI EL USUARIO ESTÁ CONVERSANDO O HACIENDO PREGUNTAS GENERALES: Mantén la conversación con el historial previo en 'text_reply'. Pon 'save_to_vault: false'.\n"
            "   - SI EL USUARIO ESTÁ DICTANDO UNA NOTA, RECORDATORIO O TAREA (ej: 'anota esto', 'comprar tal cosa', 'pensamiento:'): Pon 'save_to_vault: true', completa 'title', 'summary', 'tags', 'tasks', 'content_markdown'. En este caso 'is_conversational' DEBE SER FALSE.\n"
            "2. VOZ:\n"
            "   - Si el mensaje de entrada fue audio Y el usuario hizo una pregunta o conversación directa, pon 'is_conversational: true' y redacta en 'spoken_reply' una respuesta hablada concisa y natural (máximo 2-3 oraciones).\n"
            "   - Si fue un dictado de nota, 'is_conversational' debe ser false y 'spoken_reply' null."
        )

        contents = []
        # Agregar historial previo si existe
        for turn in recent_history:
            contents.append(turn)

        # Determinar contenido actual
        used_model = self.audio_model if audio_bytes else self.text_model
        if audio_bytes:
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            contents.append({
                "role": "user",
                "parts": [
                    audio_part,
                    {"text": "Transcribe este audio, analiza su intención según las instrucciones del sistema y responde en JSON."}
                ]
            })
        else:
            contents.append({
                "role": "user",
                "parts": [{"text": text}]
            })

        response = self.client.models.generate_content(
            model=used_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=StructuredResponse,
                temperature=0.2
            )
        )

        await self._log_tokens(user_id, used_model, "inbox_voice" if audio_bytes else "inbox_text", response)
        parsed = StructuredResponse.model_validate_json(response.text)

        # Si el usuario pidió prender la PC en el mensaje, disparar el Wake-on-LAN
        msg_str = (parsed.transcription or text or "").lower()
        if any(w in msg_str for w in ["enciende mi pc", "prende mi pc", "wake on lan", "inicia la pc"]):
            WOLService.wake_pc()

        # Guardar en memoria conversacional
        user_content = parsed.transcription if audio_bytes else text
        if user_content:
            await ConversationService.add_message(user_id=user_id, role="user", content=user_content)
        
        reply_content = parsed.spoken_reply or parsed.text_reply or parsed.summary or "Entendido."
        await ConversationService.add_message(user_id=user_id, role="model", content=reply_content)

        return parsed

    async def generate_voice_audio(self, text: str, user_id: int = 0) -> bytes:
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
