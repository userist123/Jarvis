"""
Jarvis Cognitive Brain Central Settings Configuration.
"""

import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_vault_path() -> Path:
    """Resolve the shared AI Memory Vault when available locally."""
    env_path = os.getenv("JARVIS_VAULT_PATH")
    if env_path:
        return Path(env_path).expanduser()

    module_root = Path(__file__).resolve().parents[2]
    candidates = [
        module_root.parent / "AI_Memory_Vault_CODEX_READY",
        module_root.parent.parent / "AI_Memory_Vault_CODEX_READY",
        Path("AI_Memory_Vault_CODEX_READY"),
        Path("vault_notes"),
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return Path("vault_notes")


class Settings(BaseSettings):
    """Application-wide configuration parameters."""

    model_config = SettingsConfigDict(
        env_prefix="JARVIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: Literal["ollama", "gemini", "claude", "mock"] = Field(default="ollama")
    ollama_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="qwen2.5-coder:7b")
    ollama_fast_model: str = Field(default="")
    ollama_reasoning_model: str = Field(default="")
    ollama_coding_model: str = Field(default="")
    ollama_vision_model: str = Field(default="")
    ollama_timeout: float = Field(default=30.0)
    gemini_api_key: Optional[str] = Field(default=None)
    claude_api_key: Optional[str] = Field(default=None)

    vault_path: Path = Field(default_factory=_default_vault_path)
    sync_vault: bool = Field(default=True)
    sqlite_db_path: Path = Field(default=Path("vault_memory.sqlite3"))
    sqlite_busy_timeout_ms: int = Field(default=5000)
    checkpoint_dir: Path = Field(default=Path(".checkpoints"))
    audit_log_path: Path = Field(default=Path("audit_log.jsonl"))

    allow_iot_control: bool = Field(default=False)
    allow_code_execution: bool = Field(default=False)
    allow_network: bool = Field(default=False)

    audio_driver: Literal["auto", "sounddevice", "virtual", "mock"] = Field(default="auto")
    audio_sample_rate: int = Field(default=16000)
    tts_sample_rate: int = Field(default=24000)
    vad_silence_threshold_ms: int = Field(default=500)
    vad_threshold: float = Field(default=0.5)
    vad_frame_size: int = Field(default=512)
    vad_model_path: Optional[Path] = Field(default=None)
    stt_model_size: str = Field(default="large-v3-turbo")
    stt_device: str = Field(default="auto")
    stt_compute_type: str = Field(default="int8")
    tts_voice: str = Field(default="default")
    tts_speed: float = Field(default=1.0)
    tts_model_path: Optional[Path] = Field(default=None)
    tts_voices_dir: Optional[Path] = Field(default=None)

    session_memory_path: Path = Field(default=Path(".jarvis/JARVIS_MEMORY.md"))
    recap_dir: Path = Field(default=Path(".jarvis/recaps"))
    session_memory_max_bytes: int = Field(default=3072)

    home_assistant_url: str = Field(default="http://localhost:8123")
    home_assistant_token: Optional[str] = Field(default=None)


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def reset_settings(new_settings: Optional[Settings] = None) -> Settings:
    global _settings_instance
    _settings_instance = new_settings or Settings()
    return _settings_instance
