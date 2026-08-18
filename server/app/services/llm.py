import httpx
import logging
from app.core.config import settings

log = logging.getLogger("isabel.llm")

class LLM:
    def __init__(self):
        self.base = settings.sglang_url.rstrip("/")

    async def chat(self, messages, temperature=0.2, max_tokens=2048):
        payload = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=180) as client:
            try:
                r = await client.post(f"{self.base}/v1/chat/completions", json=payload)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except httpx.ConnectError as e:
                log.warning(f"LLM connect error: {e}")
                raise RuntimeError(f"LLM offline em {self.base}") from e

    async def embed(self, texts: list[str]):
        payload = {"model": settings.embed_model, "input": texts}
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                r = await client.post(f"{self.base}/v1/embeddings", json=payload)
                if r.status_code == 404:
                    return [[0.0] * 1024 for _ in texts]
                r.raise_for_status()
                return [row["embedding"] for row in r.json()["data"]]
            except Exception:
                return [[0.0] * 1024 for _ in texts]

llm = LLM()
