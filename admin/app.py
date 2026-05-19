from fastapi import FastAPI


app = FastAPI(title="llmEvaluate Admin")


@app.get("/admin/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
