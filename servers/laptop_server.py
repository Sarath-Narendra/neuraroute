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
    result = model.infer(request.patient)
    return result