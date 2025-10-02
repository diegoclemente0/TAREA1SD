import json
import os, time, asyncio
from fastapi import FastAPI, HTTPException
import asyncpg
import redis.asyncio as aioredis
from pydantic import BaseModel

from gemini_client import call_gemini_safe
from scoring import combined_score

app = FastAPI()
DSN = os.getenv("DSN", "postgresql://postgres:examplepass@db:5432/qa")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

UPSERT_SQL = """
INSERT INTO qa_records (question_id, title, question, best_answer, llm_answer, score, first_seen, last_seen)
VALUES ($1,$2,$3,$4,$5,$6, now(), now())
ON CONFLICT (question_id) DO UPDATE SET
  llm_answer = EXCLUDED.llm_answer,
  score = EXCLUDED.score,
  times_seen = qa_records.times_seen + 1,
  last_seen = now()
RETURNING id;
"""

INSERT_LOG_SQL = """
INSERT INTO request_logs (qa_id, question_id, served_from, latency_ms, response_length, metadata)
VALUES ($1,$2,$3,$4,$5,$6);
"""

class Query(BaseModel):
    question_id: str
    title: str | None = ""
    question: str
    best_answer: str | None = ""

@app.on_event("startup")
async def startup():
    app.state.pool = await asyncpg.create_pool(dsn=DSN, min_size=1, max_size=10)
    app.state.redis = aioredis.from_url(REDIS_URL, decode_responses=True)

@app.on_event("shutdown")
async def shutdown():
    await app.state.pool.close()
    await app.state.redis.close()

@app.post("/query")
async def handle_query(q: Query):
    start = time.time()
    r = app.state.redis
    pool = app.state.pool
    key = f"q:{q.question_id}"

    cached = await r.get(key)
    if cached:
        llm_answer = cached
        served_from = "cache"
    else:
        served_from = "llm"
        try:
            llm_answer = await asyncio.to_thread(call_gemini_safe, q.question, 3, 2)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"LLM error: {e}")
        await r.set(key, llm_answer, ex=3600)

    latency = int((time.time() - start)*1000)
    combined, sem, rouge = combined_score(llm_answer, q.best_answer or "")

    async with pool.acquire() as conn:
        qa_id = await conn.fetchval(
            UPSERT_SQL,
            q.question_id,
            q.title,
            q.question,
            q.best_answer,
            llm_answer,
            float(combined)
        )
        await conn.execute(
            INSERT_LOG_SQL,
            qa_id,
            q.question_id,
            served_from,
            latency,
            len(llm_answer),
            json.dumps({"sem": sem, "rouge": rouge})
        )

    return {
        "qa_id": qa_id,
        "served_from": served_from,
        "latency_ms": latency,
        "score": combined
    }
