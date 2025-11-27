from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import time

class LoginConexaoMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        processndo_time = time.time() - start_time

        # Adiciona o tempo de processamento no cabeçalho da resposta
        response.headers["X-Process-Time"] = str(processndo_time)
        return response