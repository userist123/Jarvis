from jarvis.config import Settings
from jarvis.llm.model_router import ModelRouter


def test_default_capabilities_use_default_ollama_model():
    settings = Settings(_env_file=None)
    router = ModelRouter(settings)
    assert router.resolve("fast").model == settings.ollama_model
    assert router.resolve("reasoning").model == settings.ollama_model
    assert router.resolve("coding").model == settings.ollama_model


def test_capability_can_override_ollama_model():
    settings = Settings(_env_file=None, ollama_coding_model="qwen3-coder:30b")
    route = ModelRouter(settings).resolve("coding")
    assert route.model == "qwen3-coder:30b"


def test_unknown_capability_falls_back_to_default_model():
    settings = Settings(_env_file=None)
    route = ModelRouter(settings).resolve("unknown")
    assert route.model == settings.ollama_model
