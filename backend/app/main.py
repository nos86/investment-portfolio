from fastapi import FastAPI

app = FastAPI(title="Portfolio Tracker")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
