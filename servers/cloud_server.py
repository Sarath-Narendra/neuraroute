from fastapi import FastAPI
from pydantic import BaseModel

from models.cloud import CloudModel

app = FastAPI(
    title="NeuraRoute Cloud Server"
)

model = CloudModel()


class PatientRequest(BaseModel):
    patient: str


@app.get("/")
def health():
    return {
        "status": "running",
        "device": "cloud",
        "runtime": "Groq"
    }


@app.post("/infer")
def infer(request: PatientRequest):
    try:
        return model.infer(request.patient)
    except Exception as e:
        # No "response" key -> the engine's infer_client maps this to an error and the
        # ladder fails the task DOWN to the PC tier (e.g. no internet / no GROQ_API_KEY).
        # That failover is the demo, so the cloud tier must degrade cleanly, not 500.
        return {
            "device": "cloud",
            "runtime": model.runtime,
            "model": model.model,
            "error": str(e)
        }