from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.api import auth, ai, documents
    

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)

app.include_router(auth.router)
app.include_router(ai.router)
app.include_router(documents.router)

Instrumentator().instrument(app).expose(app)

