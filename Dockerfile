FROM python:3.13.18-slim-bookworm

WORKDIR /app

COPY requirements.txt requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --create-home appuser

COPY --chown=appuser:appgroup . .

RUN mkdir -p /app/uploads \
    && chown -R appuser:appgroup /app/uploads

USER appuser

EXPOSE 8000


CMD  ["uvicorn" ,"app.main:app", "--host=0.0.0.0"]