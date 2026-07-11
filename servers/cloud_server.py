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
    return model.infer(request.patient)