from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import cases, chat, detective, learning_progress, quiz, scam_of_day, session

app = FastAPI(
    title="Scam-Prevention-ChatBot API",
    description="Trợ lý cá nhân phòng, chống lừa đảo trực tuyến",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(cases.router, prefix="/api", tags=["cases"])
app.include_router(quiz.router, prefix="/api", tags=["quiz"])
app.include_router(scam_of_day.router, prefix="/api", tags=["scam_of_day"])
app.include_router(detective.router, prefix="/api", tags=["detective"])
app.include_router(session.router, prefix="/api", tags=["session"])
app.include_router(learning_progress.router, prefix="/api", tags=["learning_progress"])

@app.get("/health")
def health():
    return {"status": "ok"}