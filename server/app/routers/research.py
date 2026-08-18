from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from app.core.config import settings
from app.services.llm import llm
from app.services.qdrant_store import store

router = APIRouter(prefix="/research", tags=["research"])


def auth(authorization: str | None):
    if not authorization or authorization.replace("Bearer ", "") != settings.api_token:
        raise HTTPException(401, "unauthorized")


class ResearchIn(BaseModel):
    question: str


@router.post("")
async def deep_research(body: ResearchIn, authorization: str | None = Header(default=None)):
    auth(authorization)

    try:
        system = open("/app/prompts/deep_research.md", encoding="utf-8").read()
    except Exception:
        system = "Você é um motor de Deep Research local. Use evidências e cite fontes."

    plan = await llm.chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Quebre em subtarefas de pesquisa:\n{body.question}"},
        ],
        temperature=0.1,
    )

    subqueries = [q.strip("- •\t ") for q in plan.splitlines() if q.strip()][: settings.research_max_loops]
    notes = []
    evidence = []

    for sq in subqueries:
        try:
            vec = (await llm.embed([sq]))[0]
            hits = store.search(vec, top_k=settings.research_top_k)
            docs = [
                {
                    "score": h.score,
                    "text": (h.payload or {}).get("text", "")[:2000],
                    "source": (h.payload or {}).get("source", ""),
                }
                for h in hits
            ]
        except Exception:
            docs = []

        synthesis = await llm.chat(
            [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Subpergunta: {sq}\n\nEvidências:\n{docs}\n\nExtraia fatos úteis e lacunas.",
                },
            ],
            temperature=0.1,
        )
        notes.append({"query": sq, "docs": docs, "note": synthesis})
        evidence.extend(docs)

    final = await llm.chat(
        [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"Pergunta final: {body.question}\n\nNotas:\n{notes}\n\nGere relatório estruturado com fontes e incertezas.",
            },
        ],
        temperature=0.2,
        max_tokens=3500,
    )

    return {"question": body.question, "plan": subqueries, "notes": notes, "report": final}
