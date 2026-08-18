import httpx
from app.core.config import settings


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
            r = await client.post(f"{self.base}/v1/chat/completions", json=payload)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

    async def embed(self, texts: list[str]):
        payload = {"model": settings.embed_model, "input": texts}
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{self.base}/v1/embeddings", json=payload)
            if r.status_code == 404:
                return [[0.0] * 1024 for _ in texts]
            r.raise_for_status()
            data = r.json()
            return [row["embedding"] for row in data["data"]]


llm = LLM()
