import requests
import time

BASE_URL = "http://localhost:8000"
DOCUMENT_ID = 7

questions = [
    "On what date was the payment receipt issued, and how much was paid?",
    "What happened on 14 March 2026, and which individuals were involved in the communications?",
    "What documentary evidence was presented to support the claimant's case?",
    "What did the claimant and respondent disagree about regarding the manager's promise?",
    "What did the court ultimately decide, and within how many days was the refund to be made?"
]

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huZG9lIiwiZXhwIjoxNzkzMDc4NzU0fQ.Y_r1woBtcMJQpJpRQ3DvrgKw2i3beWR5PcLzS5PhdY8"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

results = []

for i, question in enumerate(questions, start=1):
    start = time.perf_counter()

    response = requests.post(
        f"{BASE_URL}/ai/ask/{DOCUMENT_ID}",
        json={"question": question},
        headers=headers,
        timeout=180
    )

    elapsed = time.perf_counter() - start

    result = {
        "question_id": f"Q{i:02}",
        "question": question,
        "status_code": response.status_code,
        "response_time_seconds": round(elapsed, 2),
        "response": response.json()
    }

    results.append(result)
    print(results)
    print(f"Q{i:02}: {response.status_code} - {elapsed:.2f}s")