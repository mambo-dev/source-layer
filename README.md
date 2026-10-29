# Document Intelligence API

The project began as a legal-document RAG application and is evolving into a reusable, containerised foundation for document-driven applications. The long-term vision is to make it adaptable to different organisations and use cases, with configurable LLM providers and agents that can connect document-derived knowledge to tools and workflows selected by the user.

The current implementation supports text-based PDF processing, hybrid retrieval using PostgreSQL and pgvector, and answer generation through a locally running Ollama model. OCR for scanned documents, alternative LLM providers, containerised deployment, and tool-using agents are planned capabilities, not yet implemented.

## Current capabilities

- User registration, login, and JWT-protected endpoints
- PDF upload and local file storage
- Page-level text extraction from text-based PDFs
- Chunking with overlap for retrieval
- Embedding generation through a local Ollama instance
- PostgreSQL + pgvector storage
- Hybrid retrieval using vector similarity, PostgreSQL full-text search, and reciprocal rank fusion
- Evidence-grounded answer generation with page-level sources
- Basic request rate limiting and Prometheus metrics exposure
- User registration, login, and JWT-protected endpoints
- SQLAlchemy models and Alembic database migrations
- Docker Compose-based development environment

## Architecture

[View on Eraser![](https://app.eraser.io/workspace/9eep9Xsz3xKJptmX0yvC/preview?diagram=_cXsWtaZYMs2ZzvC0B-f&type=embed)](https://app.eraser.io/workspace/9eep9Xsz3xKJptmX0yvC?diagram=_cXsWtaZYMs2ZzvC0B-f)
The API has two connected flows:

- **Document pipeline:** uploaded PDFs are extracted, chunked, embedded, and stored in PostgreSQL with pgvector.
- **Question pipeline:** questions trigger vector and keyword retrieval, reciprocal-rank fusion, evidence-context construction, and answer generation through Ollama.

## Project structure

```text
app/
|-- api/
|   |-- ai.py             # Question-answering endpoint
|   |-- auth.py           # Registration, login, current-user endpoint
|   `-- documents.py      # PDF upload and processing endpoint
|-- core/
|   `-- limiter.py        # Rate-limit configuration
|-- database/
|   |-- database.py       # SQLAlchemy engine and sessions
|   `-- models.py         # User, Document, and DocumentChunks models
|-- llm/
|   `-- agent_api.py      # Ollama embedding and generation client
|-- pipeline/
|   |-- context.py        # Grounded prompt construction
|   |-- ingestion.py      # PDF extraction, chunking, indexing
|   `-- retrieval.py      # Vector, keyword, and hybrid retrieval
|-- auth_helpers.py
|-- main.py
|-- schemas.py
`-- settings.py

alembic/                  # Database migrations
docs/images/              # Architecture diagram
uploads/                  # Locally stored uploaded PDFs
metrics/                  # Local timing metrics
```

## Prerequisites

For the Docker Compose setup, install:

- Docker Desktop on Windows or Docker Engine with the Compose plugin on Linux
- Git
- Sufficient disk space for container images, database data, and Ollama models
- NOTE: you don't need to install python or postgressql locally

## Quick Start with Docker Compose

### 1. Clone the Repository

```bash
git clone https://github.com/mambo-dev/source-layer.git
cd source-layer
```

### 2. Configure Environment Variables

Create a `.env` file in the directory containing the Compose file. Use the variable names expected by `app/settings.py` and your Compose configuration.

Example:

```dotenv
ENV=development

JWT_SECRET=replace-with-a-long-random-secret
ALGORITHM= your-algo
ACCESS_TOKEN_EXPIRE_MINUTES= minutes

DB_NAME=source-layer
DB_USERNAME=<DB_USERNAME>
DB_PASSWORD=replace-with-a-secure-password
DB_HOST=<DB_HOST>
DB_PORT=<PORT_NO>

API_PORT=8000
OLLAMA_PORT=11434
```

**Important:**

- These are example development values. Use a unique, secure JWT secret and database password.
- Do not commit your real `.env` file to Git.

### 3. Start the Application

From the directory containing the Compose file:

```bash
docker compose up --build -d
```

Check service status:

```bash
docker compose ps
```

View API logs:

```bash
docker compose logs -f api
```

View migration logs:

```bash
docker compose logs migrate
```

### 4. Access the API

Once the API is running, open:

- **Swagger UI:** http://localhost:8000/docs
- **OpenAPI schema:** http://localhost:8000/openapi.json
- **Metrics:** http://localhost:8000/metrics

If you change `API_PORT`, use the configured host port.

### 5. Verify the Ollama Models

Check which models the Ollama service has available:

```bash
docker compose exec ollama ollama list
```

The expected models are:

```text
nomic-embed-text:latest
llama3.2:3b
```

### 6. Stop the Application

Stop the services without deleting persistent data:

```bash
docker compose down
```

Start them again:

```bash
docker compose up -d
```

Avoid using `docker compose down -v` unless you deliberately want to delete the Compose-managed volumes, including persistent database and model data.

## Local Development Without Docker

A local Python setup is also possible if Python, PostgreSQL with pgvector, and Ollama are installed separately.

Create and activate a virtual environment, then install the project's dependencies using the dependency-management files committed to the repository.

Configure `.env` with the local database and Ollama addresses.

Download the models and start Ollama:

```bash
ollama pull nomic-embed-text
ollama pull llama3.2:3b
ollama serve
```

Apply database migrations:

```bash
alembic upgrade head
```

Start the API:

```bash
uvicorn app.main:app --reload
```

The API should then be available at http://127.0.0.1:8000/docs.

## API overview

### Register a user

```http
POST /auth/register
Content-Type: application/json
```

```json
{
  "first_name": "Jane",
  "second_name": "Doe",
  "username": "janedoe",
  "email": "jane@example.com",
  "password": "SecurePass1!",
  "confirm_password": "SecurePass1!"
}
```

### Log in

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded
```

```text
username=janedoe&password=SecurePass1!
```

The response includes a Bearer access token.

### Upload a PDF

```http
POST /documents/upload
Authorization: Bearer <access-token>
Content-Type: multipart/form-data
```

Form field:

```text
file=<your-document.pdf>
```

A successful response includes a `document_id`.

### Ask a question about a document

```http
POST /ai/ask/{document_id}
Authorization: Bearer <access-token>
Content-Type: application/json
```

```json
{
  "question": "What is the deadline stated in this document?"
}
```

Example response shape:

```json
{
  "success": true,
  "message": "Document uploaded and processed successfully",
  "data": {
    "response": "The deadline is ...",
    "sources": ["contract.pdf, Page: 3"]
  }
}
```

## Future features and optimizations

### Next steps

- [ ] **Dockerized deployment:** provide Docker images and Docker Compose services for the API, Redis, PostgreSQL with pgvector, Prometheus, and Grafana.
- [ ] **Background workers and Redis queues:** move extraction, chunking, and embedding work from the request lifecycle into Celery workers with Redis as the broker and task-result backend.
- [ ] **Asynchronous job management:** return a processing job identifier, then expose status, progress, retries, failures, and processing history.
- [ ] **Bulk document ingestion:** ingest document collections rather than requiring one-file-at-a-time uploads.
- [ ] **Google Drive ingestion:** import approved Google Drive folders or files while preserving source identifiers and metadata.
- [ ] **Amazon S3 ingestion:** import files from configured buckets or prefixes, retaining their source references and synchronization state.
- [ ] **Source synchronization:** schedule or trigger re-indexing when a connected source adds, changes, or removes documents.
- [ ] **Processing scalability:** tune worker concurrency, queue routing, embedding batch sizes, and retry policies for large collections.
- [ ] **Grafana observability:** have Prometheus scrape API and worker metrics, then build Grafana dashboards for request latency, queue depth, task success/failure rates, processing duration, retry counts, and resource use.
