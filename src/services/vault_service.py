import os
import re
from datetime import datetime
from src.config import settings

class VaultService:
    @staticmethod
    def sanitize_filename(title: str) -> str:
        clean = re.sub(r'[\\/*?:"<>|]', "", title)
        clean = clean.strip().replace(" ", "_")
        return clean[:60]

    @classmethod
    def save_note(cls, note, source_type: str = "text") -> str:
        inbox_dir = os.path.join(settings.VAULT_PATH, "Inbox")
        os.makedirs(inbox_dir, exist_ok=True)

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%Y-%m-%d %H:%M")

        filename_slug = cls.sanitize_filename(note.title or "nota_sin_titulo")
        filename = f"{date_str}_{filename_slug}.md"
        filepath = os.path.join(inbox_dir, filename)

        counter = 1
        while os.path.exists(filepath):
            filename = f"{date_str}_{filename_slug}_{counter}.md"
            filepath = os.path.join(inbox_dir, filename)
            counter += 1

        frontmatter = [
            "---",
            f"created: {time_str}",
            "tags:"
        ]
        for tag in (note.tags or []):
            frontmatter.append(f"  - {tag}")
        frontmatter.append(f"source: telegram")
        frontmatter.append(f"source_type: {source_type}")
        frontmatter.append("---\n")

        body_parts = [
            f"# {note.title or 'Nota'}\n",
            f"> [!ABSTRACT] Resumen\n> {note.summary or ''}\n"
        ]

        if getattr(note, "transcription", None):
            body_parts.append(f"### 🎙️ Transcripción Original\n> {note.transcription}\n")

        if getattr(note, "tasks", None):
            body_parts.append("### ✅ Tareas de Acción")
            for t in note.tasks:
                body_parts.append(f"- [ ] {t}")
            body_parts.append("")

        body_parts.append("### 📝 Contenido")
        body_parts.append(note.content_markdown or note.summary or "")

        content = "\n".join(frontmatter) + "\n" + "\n".join(body_parts)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath
