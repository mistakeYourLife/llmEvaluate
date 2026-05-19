from fastapi import FastAPI

from api.routes.openai_proxy import router as openai_proxy_router


app = FastAPI(title="llmEvaluate API")
app.include_router(openai_proxy_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
