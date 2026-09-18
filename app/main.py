from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title='NETRA — Privacy-First Browser Agent Backend',
    version=settings.version,
    description=(
        'Judge-ready backend for SIH PS 171. Accepts sanitized browser context, '
        'enforces a zero-trust privacy gate, optionally delegates sanitized multimodal reasoning '
        'to Qwen-VL, validates safe browser actions, and exposes a stable frontend contract.'
    ),
    docs_url='/docs',
    redoc_url='/redoc',
)

origins = [x.strip() for x in settings.cors_origins.split(',') if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ['*'],
    allow_origin_regex=r'^(chrome-extension|moz-extension|safari-web-extension)://.*$',
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(router)
