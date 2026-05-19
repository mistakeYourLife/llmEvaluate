from fastapi import FastAPI

from admin.routes.providers import router as providers_router
from admin.routes.records import router as records_router
from admin.routes.execution_tasks import router as execution_tasks_router
from admin.routes.evaluation_tasks import router as evaluation_tasks_router

app = FastAPI(title="llmEvaluate Admin")
app.include_router(providers_router)
app.include_router(records_router)
app.include_router(execution_tasks_router)
app.include_router(evaluation_tasks_router)


@app.get("/admin/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
