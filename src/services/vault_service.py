import os
import re
from datetime import datetime
from src.config import settings
from src.services.gemini_service import StructuredNote

class VaultService:
    @staticmethod
    def sanitize_filename(title: str) -> str:
        # Reemplazar caracteres no permitidos en nombres de archivo
        clean = re.sub(r'[\\/*?:"<>|]', "", title)
        clean = clean.strip().replace(" ", "_")
        return clean[:60] # Limitar longitud

    @classmethod
    def save_note(cls, note: StructuredNote, source_type: str = "text") -> str:
        inbox_dir = os.path.join(settings.VAULT_PATH, "Inbox")
        os.makedirs(inbox_dir, exist_ok=True)

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%Y-%m-%d %H:%M")

        filename_slug = cls.sanitize_filename(note.title)
        filename = f"{date_str}_{filename_slug}.md"
        filepath = os.path.join(inbox_dir, filename)

        # Si ya existe un archivo con ese nombre hoy, añadir sufijo
        counter = 1
        while os.path.exists(filepath):
            filename = f"{date_str}_{filename_slug}_{counter}.md"
            filepath = os.path.join(inbox_dir, filename)
            counter += 1

        # Construir YAML Frontmatter
        frontmatter = [
            "---",
            f"created: {time_str}",
            "tags:"
        ]
        for tag in note.tags:
            frontmatter.append(f"  - {tag}")
        frontmatter.append(f"source: telegram")
        frontmatter.append(f"source_type: {source_type}")
        frontmatter.append("---\n")

        # Construir contenido
        body_parts = [
            f"# {note.title}\n",
            f"> [!ABSTRACT] Resumen\n> {note.summary}\n"
        ]

        if note.transcription:
            body_parts.append(f"### 🎙️ Transcripción Original\n> {note.transcription}\n")

        if note.tasks:
            body_parts.append("### ✅ Tareas de Acción")
            for t in note.tasks:
                body_parts.append(f"- [ ] {t}")
            body_parts.append("")

        body_parts.append("### 📝 Contenido")
        body_parts.append(note.content_markdown)

        content = "\n".join(frontmatter) + "\n" + "\n".join(body_parts)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath
