from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from database import init_db, AsyncSessionLocal
from manager import manager

# Импортируем роутеры
from routers import auth, system_users, events, participants, directories, registrations, reports

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as session:
        await init_db(session)
    yield

app = FastAPI(
    title="Event Registration API (Hybrid)",
    description="API с JWT, RBAC и гибридной синхронизацией (WebSocket + REST)",
    version="7.6.0",
    lifespan=lifespan,
    root_path="/api"
)

# Подключаем роутеры

app.include_router(auth.router, tags=["Auth"])
app.include_router(system_users.router, tags=["System Users"])
app.include_router(directories.router, tags=["Directories"])
app.include_router(participants.router, tags=["Participants"])
app.include_router(events.router, tags=["Events"])
app.include_router(registrations.router, tags=["Registrations"])
app.include_router(reports.router, tags=["Reports"]) 

# WebSocket
@app.websocket("/ws/events/{event_id}")
async def websocket_endpoint(websocket: WebSocket, event_id: int):
    await manager.connect(websocket, event_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, event_id)
