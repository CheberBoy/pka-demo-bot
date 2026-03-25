import tempfile
import os


def transcribe_audio(audio_path: str, language: str = "ru") -> str:
    """
    Расшифровать аудиофайл через mlx-whisper.
    Возвращает текст или строку с ошибкой начинающуюся на '['.
    """
    try:
        from mlx_whisper import transcribe
        result = transcribe(audio_path, language=language, fp16=True)
        text = result.get("text", "").strip()
        return text if text else "[Не удалось распознать речь]"
    except ImportError:
        return "[mlx_whisper не установлен]"
    except Exception as e:
        return f"[Ошибка: {str(e)[:80]}]"
