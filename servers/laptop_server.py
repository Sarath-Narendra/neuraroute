from fastapi import FastAPI
from pydantic import BaseModel

from models.laptop import LaptopModel

app = FastAPI()

model = LaptopModel()


class PatientRequest(BaseModel):
    patient: str


@app.get("/")
def home():
    return {
        "device": "Laptop",
        "runtime": "GenieX",
        "status": "Running"
    }


@app.post("/infer")
def infer(request: PatientRequest):
    try:
        return model.infer(request.patient)
    except Exception as e:
        # No "response" key -> the engine's infer_client maps this to an error and the
        # ladder fails the task DOWN to the phone tier (e.g. geniex missing / model error).
        # Degrade cleanly instead of 500-ing so the failover demo stays smooth.
        return {
            "device": "laptop",
            "runtime": "GenieX",
            "model": model.model,
            "error": str(e)
        }