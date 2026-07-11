from models import run_model

tests = [
    (
        "extract_text",
        {
            "pdf_path": "sample_medical_report.pdf"
        },
        "surface"
    ),
    (
        "summarize",
        {
            "text": "Patient has fever and cough."
        },
        "surface"
    ),
    (
        "flag_risk",
        {
            "text": "Patient has BP 180/110."
        },
        "surface"
    ),
    (
        "patient_explainer",
        {
            "risks": ["High blood pressure"]
        },
        "surface"
    )
]

for op, payload, device in tests:
    print("=" * 80)
    print(op)
    print(run_model(op, payload, device))