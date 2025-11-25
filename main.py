from fastapi import FastAPI

# Создаем экземпляр приложения FastAPI
app = FastAPI(
    title="Event Registration API",
    description="API for managing users and event registrations.",
    version="1.0.0"
)

# Базовый маршрут (Root endpoint) для проверки работоспособности
@app.get("/")
def read_root():
    return {"message": "Welcome to the Event Registration API!"}

# Маршрут для проверки статуса приложения
@app.get("/status")
def get_status():
    return {"status": "Online", "framework": "FastAPI"}

# Теперь вы можете запустить приложение с помощью uvicorn
# Команда для запуска: uvicorn main:app --reload