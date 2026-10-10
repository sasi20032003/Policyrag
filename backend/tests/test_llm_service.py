"""Unit tests for the LLM service with Ollama, Anthropic, and OpenAI support."""
from unittest.mock import AsyncMock, patch

import pytest

from services.llm_service import LLMService


@pytest.mark.asyncio
async def test_llm_service_routes_to_ollama():
    service = LLMService()

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"content": "Cataract surgery is covered up to Rs 25,000 [Page 4]."}
    }
    mock_response.raise_for_status = AsyncMock()

    with patch("config.get_settings") as mock_settings:
        mock_settings.return_value.llm_provider = "ollama"
        mock_settings.return_value.ollama_base_url = "http://localhost:11434"
        mock_settings.return_value.llm_model = "llama3.2"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            answer = await service.complete(
                system_prompt="You are a policy assistant.",
                user_prompt="Is cataract surgery covered?",
            )

            assert "Cataract surgery is covered" in answer
            assert mock_post.called
            # Verify correct payload was sent to Ollama /api/chat
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["model"] == "llama3.2"
            assert call_kwargs["json"]["messages"][0]["role"] == "system"
            assert call_kwargs["json"]["messages"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_llm_service_ollama_connection_error_raises_clear_runtime_error():
    service = LLMService()

    import httpx

    with patch("config.get_settings") as mock_settings:
        mock_settings.return_value.llm_provider = "ollama"
        mock_settings.return_value.ollama_base_url = "http://localhost:11434"
        mock_settings.return_value.llm_model = "llama3.2"

        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
            with pytest.raises(RuntimeError) as exc_info:
                await service.complete(
                    system_prompt="Test system",
                    user_prompt="Test query",
                )

            assert "Cannot connect to local Ollama" in str(exc_info.value)
            assert "llama3.2" in str(exc_info.value)
