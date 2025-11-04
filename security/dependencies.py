import os
from fastapi import Header, HTTPException
from typing import Optional

API_KEY = os.getenv("IPRO_API_KEY")

async def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    """Verificação opcional de API Key para MVP"""
    if API_KEY and API_KEY != "trocar_esta_chave":
        if not x_api_key or x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="API Key inválida")
    return True

async def optional_api_key(x_api_key: Optional[str] = Header(default=None)):
    """Verificação opcional de API Key - não bloqueia se não configurada"""
    return True

