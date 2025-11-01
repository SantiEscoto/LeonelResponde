from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from time import perf_counter
import uvicorn

app = FastAPI(title="Mock Leonel Responde API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    context: Optional[str] = None
    use_knowledge_base: Optional[bool] = True
    use_memory: Optional[bool] = True
    stream: Optional[bool] = False

class QueryResponse(BaseModel):
    response: str
    processing_time: float
    tokens_used: Optional[int] = None
    context_used: Optional[bool] = None

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/status")
def status():
    return {
        "status": "ok",
        "llm": {
            "model_name": "mock-llm",
            "is_loaded": False,
            "device": "cpu",
        },
        "memory": {
            "total_users": 0,
            "total_interactions": 0,
            "short_term_entries": 0,
            "long_term_entries": 0,
        },
        "knowledge_base": {
            "total_documents": 0,
            "index_size": 0,
        },
        "uptime": 0,
    }

# Añadir endpoint de salud para pruebas rápidas
@app.get("/health")
def health():
    return {
        "status": "ok",
        "components": {
            "llm": False,
            "memory": False,
            "knowledge_base": False
        }
    }

@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    start = perf_counter()
    # Simple echo-style mock
    reply = f"Mock: recibí tu mensaje -> {req.query}"
    elapsed = perf_counter() - start
    return QueryResponse(response=reply, processing_time=elapsed, tokens_used=0, context_used=bool(req.context))

@app.post("/clear-memory")
def clear_memory():
    return {"status": "ok", "message": "Memoria limpiada (mock)"}

@app.post("/add-document")
def add_document(payload: dict):
    title = payload.get("title") or "Documento"
    return {"status": "ok", "message": f"{title} agregado (mock)"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)