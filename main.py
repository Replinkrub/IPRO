import os
import sys
from datetime import datetime, timedelta

import jwt
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from core.logger import logger, new_request_id

# Carregar variáveis de ambiente
load_dotenv()

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(__file__))

from routers.dataset_router import router as dataset_router
from routers.analytics_router import router as analytics_router
from routers.alerts_router import router as alerts_router
from routers.export_router import router as export_router

app = FastAPI(title="IPRO - Inteligência de Pedidos PRO", version="2.0.0")


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = new_request_id()
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


# Configurar CORS
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(dataset_router, prefix="/api", tags=["datasets"])
app.include_router(analytics_router, prefix="/api", tags=["analytics"])
app.include_router(alerts_router, prefix="/api", tags=["alerts"])
app.include_router(export_router, prefix="/api", tags=["export"])

# Servir arquivos estáticos
static_dir = os.path.join(os.path.dirname(__file__), "src", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health")
async def health_check():
    """Endpoint de saúde do sistema"""
    return {"status": "ok", "time": datetime.now().isoformat(), "version": "2.0.0"}


@app.get("/app-config.js")
async def app_config():
    """Configuração dinâmica para o frontend.

    Este endpoint gera um objeto JavaScript em tempo de execução com as
    configurações necessárias para o frontend, incluindo a chave de API,
    fuso horário e um JWT efêmero para autenticação.
    """
    # Gerar JWT efêmero (válido por 1 hora)
    jwt_secret = os.getenv("JWT_SECRET", "default_secret")
    payload = {
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "sub": "ipro_frontend",
    }
    # Usamos HS256 por simplicidade; em produção, recomenda‑se chave forte e rotacionada.
    token = jwt.encode(payload, jwt_secret, algorithm="HS256")

    # Construir script JavaScript com as configurações
    config_js = (
        "window.IPRO_CONFIG = {\n"
        f"    baseUrl: window.location.origin,\n"
        f"    apiKey: '{os.getenv('IPRO_API_KEY', '')}',\n"
        f"    jwt: '{token}',\n"
        f"    timezone: '{os.getenv('TIMEZONE', 'America/Sao_Paulo')}'\n"
        "};\n"
    )
    # Retornar como Response simples para evitar encapsulamento JSON
    return Response(content=config_js, media_type="application/javascript")


@app.get("/")
async def serve_index():
    """Servir a página principal"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "IPRO API está funcionando! Acesse /docs para ver a documentação."
    }


@app.get("/{path:path}")
async def serve_static_files(path: str):
    """Servir arquivos estáticos ou retornar index.html para SPA"""
    file_path = os.path.join(static_dir, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)

    # Para SPA, retornar index.html para rotas não encontradas
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)

    return {"message": f"Arquivo não encontrado: {path}"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", os.getenv("PORT", "8000"))),
        reload=True,
        limit_request_body=104857600,  # 100MB
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.detail,
            "code": exc.status_code,
            "timestamp": datetime.now().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erro interno do servidor: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "message": "Ocorreu um erro interno no servidor. Por favor, tente novamente mais tarde.",
            "code": 500,
            "timestamp": datetime.now().isoformat(),
        },
    )
