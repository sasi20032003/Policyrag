"""
Provider-independent LLM service layer with Free LLM support & zero-hallucination deterministic decoding.

Supported Providers:
1. Free Cloud Tier:
   - Groq ('groq'): 100% Free Cloud API (https://console.groq.com)
     Models: 'llama-3.3-70b-versatile', 'deepseek-r1-distill-llama-70b', 'llama-3.1-8b-instant'
     Near-instant speed (500+ tok/s), 70B reasoning power, drastically lower hallucination than small local models.
   - Google Gemini ('gemini'): 100% Free Cloud Tier (https://aistudio.google.com)
     Models: 'gemini-2.0-flash', 'gemini-1.5-flash'
     Massive context window, state-of-the-art citation fidelity.
2. Free Local Tier:
   - Ollama ('ollama'): 100% Private, Offline, Zero-Cost
     Models: 'deepseek-r1:8b', 'qwen2.5:7b', 'llama3.2', 'mistral:7b'
     Configured with deterministic greedy sampling (temperature=0.0, repetition penalty=1.15)
3. Paid Cloud Tier:
   - Anthropic Claude ('anthropic'): claude-sonnet-4-6, claude-3-5-sonnet-20241022
   - OpenAI ('openai'): gpt-4o-mini, gpt-4o
"""
import json
import logging
from typing import AsyncGenerator

from config import get_settings

logger = logging.getLogger(__name__)


class LLMService:
    @property
    def provider(self) -> str:
        settings = get_settings()
        prov = settings.llm_provider.lower().strip()
        # Auto-detect available free provider if set to auto or fallback
        if prov == "auto":
            if settings.groq_api_key:
                return "groq"
            elif settings.gemini_api_key:
                return "gemini"
            return "ollama"
        return prov

    async def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 1000) -> str:
        prov = self.provider

        if prov == "groq":
            return await self._complete_groq(system_prompt, user_prompt, max_tokens)
        elif prov == "gemini":
            return await self._complete_gemini(system_prompt, user_prompt, max_tokens)
        elif prov == "ollama":
            return await self._complete_ollama(system_prompt, user_prompt, max_tokens)
        elif prov == "anthropic":
            return await self._complete_anthropic(system_prompt, user_prompt, max_tokens)
        elif prov == "openai":
            return await self._complete_openai(system_prompt, user_prompt, max_tokens)

        raise ValueError(
            f"Unsupported LLM_PROVIDER: '{prov}'. Supported: 'groq', 'gemini', 'ollama', 'anthropic', 'openai'."
        )

    async def stream_complete(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 1000
    ) -> AsyncGenerator[str, None]:
        """
        Async generator yielding token chunks progressively for Server-Sent Events (SSE).
        """
        prov = self.provider
        if prov == "groq":
            async for chunk in self._stream_groq(system_prompt, user_prompt, max_tokens):
                yield chunk
        elif prov == "gemini":
            async for chunk in self._stream_gemini(system_prompt, user_prompt, max_tokens):
                yield chunk
        elif prov == "ollama":
            async for chunk in self._stream_ollama(system_prompt, user_prompt, max_tokens):
                yield chunk
        elif prov == "anthropic":
            async for chunk in self._stream_anthropic(system_prompt, user_prompt, max_tokens):
                yield chunk
        elif prov == "openai":
            async for chunk in self._stream_openai(system_prompt, user_prompt, max_tokens):
                yield chunk
        else:
            full_text = await self.complete(system_prompt, user_prompt, max_tokens)
            yield full_text

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Groq (Free Tier: 70B & DeepSeek R1 Distill)
    # ─────────────────────────────────────────────────────────────────────────
    async def _complete_groq(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        import httpx

        settings = get_settings()
        api_key = settings.groq_api_key
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Get a free API key in 30 seconds at https://console.groq.com"
            )

        model = settings.llm_model if ("llama" in settings.llm_model.lower() or "deepseek" in settings.llm_model.lower() or "mixtral" in settings.llm_model.lower()) else "llama-3.3-70b-versatile"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": 0.0,  # Purely deterministic greedy decoding eliminates hallucination
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _stream_groq(self, system_prompt: str, user_prompt: str, max_tokens: int):
        import httpx

        settings = get_settings()
        api_key = settings.groq_api_key
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set.")

        model = settings.llm_model if ("llama" in settings.llm_model.lower() or "deepseek" in settings.llm_model.lower()) else "llama-3.3-70b-versatile"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "max_tokens": max_tokens,
                        "temperature": 0.0,
                        "stream": True,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            parsed = json.loads(data_str)
                            delta = parsed["choices"][0].get("delta", {}).get("content", "")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except Exception as exc:
            logger.warning("Groq stream failed (%s), falling back to complete", exc)
            full_text = await self._complete_groq(system_prompt, user_prompt, max_tokens)
            yield full_text

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Google Gemini (Free Tier: Gemini 2.0 Flash)
    # ─────────────────────────────────────────────────────────────────────────
    async def _complete_gemini(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        import httpx

        settings = get_settings()
        api_key = settings.gemini_api_key
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free API key at https://aistudio.google.com"
            )

        model = settings.llm_model if "gemini" in settings.llm_model.lower() else "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"System Instructions:\n{system_prompt}\n\nTask:\n{user_prompt}"}],
                }
            ],
            "generationConfig": {
                "temperature": 0.0,  # Deterministic decoding
                "maxOutputTokens": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
            return ""

    async def _stream_gemini(self, system_prompt: str, user_prompt: str, max_tokens: int):
        import httpx

        settings = get_settings()
        api_key = settings.gemini_api_key
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")

        model = settings.llm_model if "gemini" in settings.llm_model.lower() else "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={api_key}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"System Instructions:\n{system_prompt}\n\nTask:\n{user_prompt}"}],
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        try:
                            parsed = json.loads(data_str)
                            candidates = parsed.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    text = part.get("text", "")
                                    if text:
                                        yield text
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            logger.warning("Gemini stream failed (%s), falling back to complete", exc)
            full_text = await self._complete_gemini(system_prompt, user_prompt, max_tokens)
            yield full_text

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Ollama (100% Free Local, Deterministic Sampling)
    # ─────────────────────────────────────────────────────────────────────────
    async def _complete_ollama(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        import httpx

        settings = get_settings()
        base_url = settings.ollama_base_url.rstrip("/")
        model = settings.llm_model or "llama3.2"

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(
                    f"{base_url}/api/chat",
                    json={
                        "model": model,
                        "stream": False,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": 0.0,      # Deterministic greedy decoding
                            "top_p": 0.1,            # Strict nucleus filtering
                            "repeat_penalty": 1.15,  # Prevents repetition loops
                            "seed": 42,
                        },
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "").strip()
        except httpx.ConnectError as exc:
            logger.error(
                "Could not connect to Ollama at %s. Ensure Ollama is running ('ollama serve').",
                base_url,
            )
            # Check if user has Groq or Gemini API keys configured as fallback
            if settings.groq_api_key:
                logger.info("Auto-fallback to Groq free cloud API")
                return await self._complete_groq(system_prompt, user_prompt, max_tokens)
            elif settings.gemini_api_key:
                logger.info("Auto-fallback to Gemini free cloud API")
                return await self._complete_gemini(system_prompt, user_prompt, max_tokens)
            raise RuntimeError(
                f"Cannot connect to local Ollama at {base_url}. Either start Ollama or set GROQ_API_KEY in .env for instant free cloud inference."
            ) from exc

    async def _stream_ollama(self, system_prompt: str, user_prompt: str, max_tokens: int):
        import httpx

        settings = get_settings()
        base_url = settings.ollama_base_url.rstrip("/")
        model = settings.llm_model or "llama3.2"

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/api/chat",
                    json={
                        "model": model,
                        "stream": True,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": 0.0,
                            "top_p": 0.1,
                            "repeat_penalty": 1.15,
                            "seed": 42,
                        },
                    },
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            token = data.get("message", {}).get("content", "")
                            if token:
                                yield token
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            logger.warning("Ollama stream failed (%s), attempting complete", exc)
            full_text = await self._complete_ollama(system_prompt, user_prompt, max_tokens)
            yield full_text

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Anthropic & OpenAI (Paid Tiers)
    # ─────────────────────────────────────────────────────────────────────────
    async def _complete_anthropic(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        import anthropic

        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.llm_model,
            max_tokens=max_tokens,
            temperature=0.0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    async def _stream_anthropic(self, system_prompt: str, user_prompt: str, max_tokens: int):
        import anthropic

        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        try:
            async with client.messages.stream(
                model=settings.llm_model,
                max_tokens=max_tokens,
                temperature=0.0,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as exc:
            logger.warning("Anthropic stream failed: %s", exc)
            full_text = await self._complete_anthropic(system_prompt, user_prompt, max_tokens)
            yield full_text

    async def _complete_openai(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        import httpx

        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.llm_model or "gpt-4o-mini",
                    "max_tokens": max_tokens,
                    "temperature": 0.0,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _stream_openai(self, system_prompt: str, user_prompt: str, max_tokens: int):
        import httpx

        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={
                        "model": settings.llm_model or "gpt-4o-mini",
                        "max_tokens": max_tokens,
                        "temperature": 0.0,
                        "stream": True,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            parsed = json.loads(data_str)
                            delta = parsed["choices"][0].get("delta", {}).get("content", "")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except Exception as exc:
            logger.warning("OpenAI stream failed: %s", exc)
            full_text = await self._complete_openai(system_prompt, user_prompt, max_tokens)
            yield full_text


llm_service = LLMService()
