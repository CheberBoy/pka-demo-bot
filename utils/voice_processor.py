import os
import tempfile


def transcribe_audio(audio_path: str, language: str = "ru") -> str:
    """
    Расшифровать аудиофайл.
    Mac (Apple Silicon): mlx_whisper
    Linux/Railway: faster_whisper (tiny модель, CPU)
    Возвращает текст или строку с ошибкой начинающуюся на '['.
    """
    # Сначала пробуем mlx_whisper (только Mac/Apple Silicon)
    try:
        from mlx_whisper import transcribe
        result = transcribe(audio_path, language=language, fp16=True)
        text = result.get("text", "").strip()
        return text if text else "[Не удалось распознать речь]"
    except ImportError:
        pass  # Не Mac — идём дальше
    except Exception as e:
        return f"[mlx_whisper ошибка: {str(e)[:80]}]"

    # Fallback: faster_whisper (работает на Linux/Railway CPU)
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_path, language=language)
        text = " ".join(seg.text for seg in segments).strip()
        return text if text else "[Не удалось распознать речь]"
    except ImportError:
        return "[faster_whisper не установлен]"
    except Exception as e:
        return f"[Ошибка: {str(e)[:80]}]"
