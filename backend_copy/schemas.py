from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

# --- Схемы для Авторизации ---
class SourceDocument(BaseModel):
    """Схема для одного документа-источника (контекст и метаданные)."""
    filepath: str = Field(..., description="Локальный путь к документу-источнику (для ссылки).")
    content: str = Field(..., description="Контекст (сниппет), извлеченный из документа.")
    # Добавьте любые другие поля из вашего payload, если они нужны на фронтенде
    # например: page_number: Optional[int] = None
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str
    
class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    username: Optional[str] = None

# --- Схемы для Чатов и Сообщений ---

class MessageBase(BaseModel):
    content: str
    sender: str # 'user' или 'ai'

class MessageCreate(MessageBase):
    pass # Наследует content и sender
    
class Message(MessageBase):
    id: int
    chat_id: int
    timestamp: datetime = Field(..., alias="created_at")
    source_documents: Optional[List[SourceDocument]] = None
    class Config:
        from_attributes = True

class ChatBase(BaseModel):
    title: str = "Новый чат"

class ChatCreate(ChatBase):
    pass

class Chat(ChatBase):
    id: int
    user_id: int
    created_at: datetime
    
    # Дополнительно можно включить сообщения для истории
    messages: List[Message] = [] 

    class Config:
        from_attributes = True