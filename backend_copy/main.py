import asyncio
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from database import get_db, User, create_db_tables 
from schemas import UserCreate, Token, UserLogin, Chat as ChatSchema, Message as MessageSchema, ChatCreate 
from auth import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
from datetime import timedelta
import crud
from pydantic import BaseModel
from typing import List
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from main_rag import initialize_rag_resources, get_rag_answer 
RAW_DIR = Path("data/raw")

# Создаем таблицы при запуске (если еще не созданы)
create_db_tables() 

app = FastAPI()

# --- ИНИЦИАЛИЗАЦИЯ RAG-РЕСУРСОВ ПРИ ЗАПУСКЕ СЕРВЕРА ---
@app.on_event("startup")
def startup_event():
    # Загружаем LLM, эмбеддинги и FAISS-индекс один раз
    if not initialize_rag_resources():
        # Если инициализация не удалась, можно остановить приложение или выдать предупреждение
        print("ВНИМАНИЕ: RAG-ресурсы не были загружены. Чат будет недоступен или будет выдавать ошибки.")
# -------------------------------------------------------

@app.get("/files/{filename}")
async def get_file(filename: str):
    file_path = RAW_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        return {"error": "File not found"}
    return FileResponse(path=file_path, filename=filename)

# --- Настройка CORS ---
origins = [
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --------------------

# --- Эндпоинты Аутентификации ---

@app.post("/register", response_model=Token)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=Token)
def login_for_access_token(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "id": current_user.id}


# --- УПРАВЛЕНИЕ ЧАТАМИ ---

@app.post("/chats/", response_model=ChatSchema, status_code=status.HTTP_201_CREATED)
def create_new_chat(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Создает новый пустой чат."""
    return crud.create_user_chat(db=db, user_id=current_user.id, title="Новый чат")

@app.get("/chats/", response_model=List[ChatSchema])
def read_user_chats(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Возвращает список всех чатов текущего пользователя."""
    return crud.get_user_chats(db=db, user_id=current_user.id)

@app.delete("/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_chat(
    chat_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Удаляет чат, если пользователь является его владельцем."""
    owner_id = crud.get_chat_owner_id(db, chat_id)
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    if owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this chat")
    crud.delete_chat(db, chat_id)
    return 

@app.get("/chats/{chat_id}/messages", response_model=List[MessageSchema])
def read_chat_messages(
    chat_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Возвращает историю сообщений для конкретного чата."""
    owner_id = crud.get_chat_owner_id(db, chat_id)
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    if owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this chat")
    return crud.get_messages_by_chat_id(db, chat_id)


# --- ОБНОВЛЕННЫЙ ЭНДПОИНТ ЧАТА (/chat) ---

class ChatRequest(BaseModel):
    query: str
    chat_id: int 
    use_tables: bool = False # <-- НОВОЕ ПОЛЕ: Флаг для поиска в табличном индексе
    
@app.post("/chat", response_model=MessageSchema)
async def process_chat_request(
    request: ChatRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # 1. Проверка владения чатом
    owner_id = crud.get_chat_owner_id(db, request.chat_id)
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    if owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to use this chat")

    # 2. Логика именования чата при первом сообщении
    message_count = crud.get_message_count_by_chat_id(db, request.chat_id)
    db_user_message = crud.create_message(db, request.chat_id, request.query, sender="user")
    
    if message_count == 0:
        new_title = request.query[:30].strip()
        if len(request.query) > 30:
            new_title += "..."
        crud.update_chat_title(db, request.chat_id, new_title)
    
    # 3. ПОЛУЧЕНИЕ ИСТОРИИ ЧАТА ДЛЯ КОНТЕКСТА
    # Получаем все сообщения, включая только что добавленное пользователем
    previous_messages_db = crud.get_messages_by_chat_id(db, request.chat_id)
    
    # Формируем историю для RAG: исключаем только что добавленное сообщение, 
    # так как его текст передается отдельно в 'request.query'
    history_for_rag = [
        (msg.sender, msg.content) 
        for msg in previous_messages_db 
        if msg.id != db_user_message.id 
    ]
    history_for_rag = history_for_rag[-20:]
    
    # 4. ВЫЗОВ РЕАЛЬНОГО RAG-ДВИЖКА
    try:
        # get_rag_answer синхронная, поэтому используем asyncio.to_thread, чтобы не блокировать сервер
        rag_result = await asyncio.to_thread(
            get_rag_answer, 
            history_for_rag, 
            request.query, 
            use_tables=request.use_tables # <-- Передаем новый флаг!
        )
        answer_text = rag_result.get("answer", "Ошибка при получении ответа от RAG-движка.")
        source_documents = rag_result.get("source_documents", [])
        
    except Exception as e:
        # В случае ошибки RAG, возвращаем сообщение об ошибке
        print(f"Критическая ошибка RAG: {e}")
        answer_text = "Извините, произошла внутренняя ошибка сервера при обработке запроса AI."
        source_documents = []
        
    # 5. Сохраняем ответ AI (только текст в БД)
    db_ai_message = crud.create_message(db, request.chat_id, answer_text, sender="ai")

    # 6. Возвращаем сообщение AI + источники
    response = MessageSchema.model_validate(db_ai_message)
    response.source_documents = source_documents
    return response