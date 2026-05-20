import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

os.environ["TOKENIZERS_PARALLELISM"] = "false"
sys.path.append(str(Path(__file__).parent))

load_dotenv()

from sentence_transformers import SentenceTransformer
from supabase import create_client

app = FastAPI(title="AILEVATED Brain API")

print("🚀 Loading embedding model...")
embed_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device='cpu')
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
print("✅ Ready.")


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 5

class PlannerRequest(BaseModel):
    subject: str
    grade: str
    topic: str
    duration: int = 45
    language: str = "ar"
    lesson_type: str = "new_concept"
    track: Optional[str] = None
    provider: Optional[str] = None  # groq | gemini | anthropic


@app.get("/health")
async def health():
    return {"status": "ok", "message": "AILEVATED Brain is running"}


@app.post("/api/retrieve")
async def retrieve(request: RetrieveRequest):
    query_embedding = embed_model.encode(request.query).tolist()
    result = supabase.rpc("match_curriculum_chunks", {
        "query_embedding": query_embedding,
        "match_threshold": 0.18,
        "match_count": request.top_k
    }).execute()
    return {"chunks": result.data, "total": len(result.data)}

@app.get("/api/providers")
async def check_providers():
    """Shows which LLM providers are available based on configured API keys."""
    from core.llm_provider import PROVIDERS
    status = {}
    for name, config in PROVIDERS.items():
        key = os.getenv(config["key_env"])
        status[name] = {
            "available": bool(key and len(key) > 10),
            "models": config["models"]
        }
    active = os.getenv("LLM_PROVIDER") or "auto"
    return {"active_provider": active, "providers": status}


@app.post("/api/planner")
async def planner(request: PlannerRequest):
    try:
        from core.graph import lesson_graph
        
        print(f"📋 Request provider: {request.provider}")
        
        result = lesson_graph.invoke({
            "subject": request.subject,
            "grade": request.grade,
            "topic": request.topic,
            "duration": request.duration,
            "language": request.language,
            "lesson_type": request.lesson_type,
            "track": request.track,
            "provider": request.provider,
            "curriculum_context": "",
            "learning_objectives": {},
            "lesson_structure": "",
            "lesson_plan": {},
            "support_variant": None,
            "extension_variant": None,
            "quality_score": None,
            "error": "",
            "chunks_used": []
        })
        
        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "status": "success",
            "data": {
                "lesson_plan": result["lesson_plan"],
                "differentiation": {
                    "support": result.get("support_variant"),
                    "extension": result.get("extension_variant")
                },
                "quality_score": result.get("quality_score")
            },
            "curriculum_alignment": {
                "sources_used": [
                    {
                        "source": c["source"],
                        "similarity": round(c["similarity"], 2),
                        "excerpt": c["content"][:150] + "..."
                    }
                    for c in result.get("chunks_used", [])
                ],
                "alignment_score": round(
                    sum(c["similarity"] for c in result.get("chunks_used", [])) /
                    max(len(result.get("chunks_used", [])), 1), 2
                )
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/planner/stream")
async def planner_stream(request: PlannerRequest):
    async def generate():
        try:
            from core.graph import lesson_graph
            import json

            result = lesson_graph.invoke({
                "subject": request.subject,
                "grade": request.grade,
                "topic": request.topic,
                "duration": request.duration,
                "language": request.language,
                "lesson_type": request.lesson_type,
                "track": request.track,
                "curriculum_context": "",
                "learning_objectives": {},
                "lesson_structure": "",
                "lesson_plan": {},
                "support_variant": None,
                "extension_variant": None,
                "quality_score": None,
                "error": "",
                "chunks_used": []
            })

            if result.get("error"):
                yield f"Error: {result['error']}"
                return

            output = json.dumps({
                "status": "success",
                "data": {
                    "lesson_plan": result["lesson_plan"],
                    "differentiation": {
                        "support": result.get("support_variant"),
                        "extension": result.get("extension_variant")
                    },
                    "quality_score": result.get("quality_score")
                },
                "curriculum_alignment": {
                    "sources_used": [
                        {
                            "source": c["source"],
                            "similarity": round(c["similarity"], 2),
                            "excerpt": c["content"][:150] + "..."
                        }
                        for c in result.get("chunks_used", [])
                    ],
                    "alignment_score": round(
                        sum(c["similarity"] for c in result.get("chunks_used", [])) /
                        max(len(result.get("chunks_used", [])), 1), 2
                    )
                }
            }, ensure_ascii=False, indent=2)

            chunk_size = 100
            for i in range(0, len(output), chunk_size):
                yield output[i:i + chunk_size]

        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(generate(), media_type="text/plain")