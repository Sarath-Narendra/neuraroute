from fastapi import FastAPI
from pydantic import BaseModel

from models.phone import PhoneModel

app = FastAPI(
    title="NeuraRoute Phone Server"
)

model = PhoneModel()


class PatientRequest(BaseModel):
    patient: str


@app.get("/")
def health():
    return {
        "status": "running",
        "device": "phone",
        "runtime": model.runtime,
        "model": model.model
    }


@app.post("/infer")
def infer(request: PatientRequest):
    try:
        return model.infer(request.patient)
    except Exception as e:
        # Deliberately NO "response" key: the engine's infer_client reads that as an error
        # and fails the task DOWN the ladder to the arduino tier. That failover is the demo,
        # so a dead phone model must degrade cleanly instead of 500-ing.
        return {
            "device": "phone",
            "runtime": model.runtime,
            "model": model.model,
            "error": str(e)
        }
