from fastapi import FastAPI

from admin.routes.providers import router as providers_router

app = FastAPI(title="llmEvaluate Admin")
app.include_router(providers_router)


@app.get("/admin/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
