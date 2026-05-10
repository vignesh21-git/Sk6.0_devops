from fastapi import FastAPI

app = FastAPI(title="Sk6.0", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}
