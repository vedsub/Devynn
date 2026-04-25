"""
ASR service – thin wrapper around asr.asr_func for future extensibility
(e.g. S3 upload, caching, metrics).
"""

from asr.asr_func import audio_to_text, transcribe_audio, calculate_speaking_pace

__all__ = ["audio_to_text", "transcribe_audio", "calculate_speaking_pace"]
