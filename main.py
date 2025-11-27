from fastapi import FastAPI
from routes import chat_rotas
from middlwares.login_conexao import LoginConexaoMiddleware

app = FastAPI(
    title="Banco Ágil API",
    version="1.0.0",
    description="API para gerenciamento do Webchat do Banco Ágil",
)

app.add_middleware(LoginConexaoMiddleware)
app.include_router(chat_rotas.router, prefix="/chat", tags=["Chat"])

app.get("/")
def home():
    return {"Status": "API do Banco Ágil está rodando!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
