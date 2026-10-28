FROM python:3.13.18-slim-bookworm

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD  ["uvicorn" ,"app.main:app", "--host=0.0.0.0"]