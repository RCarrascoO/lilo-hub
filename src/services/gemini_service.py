import io
import wave
from typing import Optional, List
from pydantic import BaseModel
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from src.config import settings
from src.services.token_service import TokenService
from src.services.system_service import SystemService
from src.services.wol_service import WOLService
from src.services.conversation_service import ConversationService
from src.services.google_service import google_service
from src.utils.date_utils import get_now, format_spanish_date, format_relative_event_time

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
    action: Optional[str] = None
    reminder_minutes: Optional[int] = None
    reminder_text: Optional[str] = None

class GeminiService:
    def __init__(self):
        api_key = settings.GEMINI_API_KEY or "AIzaSyDummyKeyForTestingTestingTesting"
        self.client = genai.Client(api_key=api_key)
        # Piscinas de modelos con cascada automática para sortear límites de cuota (429)
        self.text_models = ["gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-flash-latest"]
        self.audio_models = ["gemini-flash-latest", "gemini-3.5-flash", "gemini-2.5-flash"]
        self.pro_models = ["gemini-2.5-pro", "gemini-pro-latest"]
        self.tts_models = ["gemini-2.5-flash-preview-tts", "gemini-3.8-flash-tts"]

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
        try:
            m = SystemService.get_metrics()
            ram = m["ram"]
            containers_str = ", ".join([f"{c['name']} ({c['status']})" for c in m["containers"]])
            disks_str = ", ".join([f"{d['name']}: {d['free_gb']}GB libres de {d['total_gb']}GB" for d in m["disks"]])
            return (
                f"ESTADO DEL SERVIDOR EN VIVO:\n"
                f"- CPU: {m['cpu_percent']}% ({m['cpu_count']} cores)\n"
                f"- RAM: {ram['used_gb']} GB usados de {ram['total_gb']} GB ({ram['percent']}%), libres: {ram['free_gb']} GB\n"
                f"- Discos: {disks_str}\n"
                f"- Contenedores Docker activos: {containers_str}"
            )
        except Exception as e:
            return f"Estado del servidor: Error consultando metricas: {e}"

    def _get_live_google_context(self) -> str:
        try:
            if not google_service.is_authenticated():
                return "ESTADO DE GOOGLE WORKSPACE: No autenticado actualmente."
            events = google_service.get_calendar_events(days=3, max_results=6)
            emails = google_service.get_unread_emails(max_results=5)

            events_lines = []
            if events:
                for e in events:
                    formatted_time = format_relative_event_time(e['start'], e.get('is_all_day', False))
                    events_lines.append(f"• {formatted_time}: {e['summary']}")
                events_str = "\n".join(events_lines)
            else:
                events_str = "Sin eventos próximos"

            emails_lines = []
            if emails:
                for e in emails:
                    sender = e['sender'].split('<')[0].strip().replace('"', '')
                    emails_lines.append(f"• De {sender}: {e['subject']}")
                emails_str = "\n".join(emails_lines)
            else:
                emails_str = "Sin correos no leídos"

            return (
                f"ESTADO DE GOOGLE WORKSPACE EN VIVO:\n"
                f"- Próximos eventos Calendar:\n{events_str}\n"
                f"- Correos Gmail no leídos recientes:\n{emails_str}"
            )
        except Exception as e:
            return f"ESTADO DE GOOGLE WORKSPACE: Error consultando ({e})"

    async def process_message(
        self,
        text: Optional[str] = None,
        audio_bytes: Optional[bytes] = None,
        mime_type: str = "audio/ogg",
        user_id: int = 0
    ) -> StructuredResponse:
        recent_history = await ConversationService.get_recent_history(user_id=user_id, limit=6)
        server_ctx = self._get_live_server_context()
        google_ctx = self._get_live_google_context()
        now = get_now()
        fecha_exacta = format_spanish_date(now)

        system_instruction = (
            f"Eres Lilo Hub, el orquestador y asistente personal de {settings.USER_NAME}. Tienes acceso directo a su servidor, a su Google Calendar, a su Gmail y a su bóveda de Obsidian.\n\n"
            f"FECHA Y HORA ACTUAL EN VIVO (Zona horaria Chile / Santiago):\n"
            f"- Hoy es: {fecha_exacta}\n\n"
            f"{server_ctx}\n\n"
            f"{google_ctx}\n\n"
            "INSTRUCCIONES CLAVE:\n"
            "1. DISCRIMINACIÓN DE INTENCIÓN:\n"
            "   - SI EL USUARIO PIDE DATOS DEL SERVIDOR (CPU, RAM, Docker, estado): Usa los datos en vivo provistos arriba. Responde con precisión en 'text_reply' y si es audio también en 'spoken_reply'. Pon 'save_to_vault: false' (NO guardes notas en Obsidian de consultas del servidor).\n"
            "   - SI EL USUARIO PREGUNTA POR GOOGLE (Gmail, Calendar, agenda, eventos o correos): Usa los datos en vivo provistos de Google Workspace arriba (¡TIENES ACCESO COMPLETO, jamás digas que no tienes acceso o que faltan credenciales!). Responde con precisión en 'text_reply' y 'spoken_reply'. Pon 'save_to_vault: false'.\n"
            "   - SI EL USUARIO PIDE ENCENDER SU PC: Confírmale que enviarás el paquete Wake-on-LAN, pon 'action: wake_pc', 'save_to_vault: false'.\n"
            "   - SI EL USUARIO PIDE UN RECORDATORIO O TEMPORIZADOR (ej: 'recuérdame en 5 minutos hacer X', 'pon una alarma en 10 min'): Pon 'action: reminder', 'reminder_minutes: <numero_en_minutos>', 'reminder_text: <motivo>', 'save_to_vault: false'. Confirma en 'text_reply' / 'spoken_reply' que programaste el recordatorio.\n"
            "   - SI EL USUARIO ESTÁ CONVERSANDO O HACIENDO PREGUNTAS GENERALES: Mantén la conversación con el historial previo en 'text_reply'. Pon 'save_to_vault: false'.\n"
            "   - SI EL USUARIO ESTÁ DICTANDO UNA NOTA PARA GUARDAR (ej: 'anota esto', 'guarda esta idea', 'pensamiento:'): Pon 'save_to_vault: true', completa 'title', 'summary', 'tags', 'tasks', 'content_markdown'. En este caso 'is_conversational' DEBE SER FALSE.\n"
            "2. VOZ:\n"
            "   - Si el mensaje de entrada fue audio Y el usuario hizo una pregunta o pidió una acción directa, pon 'is_conversational: true' y redacta en 'spoken_reply' una respuesta hablada concisa y natural (máximo 2-3 oraciones).\n"
            "   - Si fue un dictado de nota, 'is_conversational' debe ser false y 'spoken_reply' null."
        )

        contents = []
        for turn in recent_history:
            contents.append(turn)

        candidate_models = self.audio_models if audio_bytes else self.text_models
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

        response = None
        last_error = None
        used_model = candidate_models[0]

        # Cascada de modelos ante límites de cuota (429) o errores temporales
        for model_name in candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=StructuredResponse,
                        temperature=0.2
                    )
                )
                used_model = model_name
                break
            except ClientError as ce:
                last_error = ce
                if ce.code == 429:
                    print(f"Cuota agotada en {model_name} (429). Probando siguiente modelo de la piscina...")
                    continue
                raise ce
            except Exception as e:
                last_error = e
                print(f"Error con modelo {model_name}: {e}. Intentando fallback...")
                continue

        if not response:
            raise RuntimeError(f"Todos los modelos de la piscina agotaron su cuota o fallaron: {last_error}")

        await self._log_tokens(user_id, used_model, "inbox_voice" if audio_bytes else "inbox_text", response)
        parsed = StructuredResponse.model_validate_json(response.text)

        # Si el usuario pidió prender la PC en el mensaje, disparar el Wake-on-LAN
        msg_str = (parsed.transcription or text or "").lower()
        if any(w in msg_str for w in ["enciende mi pc", "prende mi pc", "wake on lan", "inicia la pc"]):
            WOLService.wake_pc()

        user_content = parsed.transcription if audio_bytes else text
        if user_content:
            await ConversationService.add_message(user_id=user_id, role="user", content=user_content)
        
        reply_content = parsed.spoken_reply or parsed.text_reply or parsed.summary or "Entendido."
        await ConversationService.add_message(user_id=user_id, role="model", content=reply_content)

        return parsed

    async def generate_voice_audio(self, text: str, user_id: int = 0) -> bytes:
        response = None
        used_model = self.tts_models[0]
        for m in self.tts_models:
            try:
                response = self.client.models.generate_content(
                    model=m,
                    contents=text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"]
                    )
                )
                used_model = m
                break
            except Exception as e:
                print(f"Falla en TTS con {m}: {e}, probando fallback...")
                continue

        if not response:
            raise RuntimeError("No se pudo generar audio con los modelos TTS disponibles.")

        await self._log_tokens(user_id, used_model, "tts_voice_reply", response)

        pcm_data = response.candidates[0].content.parts[0].inline_data.data
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(pcm_data)
        return wav_io.getvalue()

    async def query_pro_model(self, query: str, user_id: int = 0) -> str:
        now = get_now()
        fecha_exacta = format_spanish_date(now)
        prompt = (
            f"Eres Lilo Hub en Modo Pro (Gemini 2.5 Pro). Actúas como consultor y tutor experto de {settings.USER_NAME}. "
            f"La fecha y hora actual en vivo es {fecha_exacta} (Santiago de Chile).\n"
            "Brinda una respuesta profunda, rigurosa, clara y estructurada en Markdown.\n\n"
            f"Consulta del usuario:\n{query}"
        )
        response = None
        used_model = self.pro_models[0]
        for m in self.pro_models:
            try:
                response = self.client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.3)
                )
                used_model = m
                break
            except Exception as e:
                print(f"Error en {m}: {e}, probando fallback...")
                continue

        if not response:
            raise RuntimeError("Los modelos Pro están temporalmente saturados.")

        await self._log_tokens(user_id, used_model, "pro_reasoning", response)
        return response.text

    async def generate_briefing_text(self, prompt: str, user_id: int = 0) -> str:
        response = None
        used_model = self.text_models[0]
        for m in self.text_models:
            try:
                response = self.client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.7)
                )
                used_model = m
                break
            except Exception as e:
                print(f"Error en {m} para briefing: {e}, probando fallback...")
                continue

        if not response:
            raise RuntimeError("Los modelos de texto están temporalmente saturados.")

        await self._log_tokens(user_id, used_model, "morning_briefing", response)
        return response.text

gemini_service = GeminiService()
