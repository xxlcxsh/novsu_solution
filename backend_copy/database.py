from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase
from datetime import datetime
import os

# --- 1. Настройка подключения ---
# Имя файла SQLite будет project.db в корне папки backend
DATABASE_URL = "sqlite:///./project.db"

# Создание движка SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} # Необходимо для SQLite в FastAPI
)

# --- 2. Базовый класс для моделей ---
class Base(DeclarativeBase):
    pass

# --- 3. Определение Моделей ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Связь с чатами
    chats = relationship("Chat", back_populates="owner", cascade="all, delete-orphan")

class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, default="Новый чат")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    owner = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    content = Column(Text, nullable=False)
    sender = Column(String, nullable=False) # 'user' или 'ai'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # НОВОЕ ПОЛЕ: Для хранения сериализованных данных об источниках RAG
    source_documents_json = Column(Text, nullable=True) 

    chat = relationship("Chat", back_populates="messages")


# --- 4. Создание сессий и инициализация БД ---

# Создание класса сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Функция для создания таблиц (вызывается один раз)
def create_db_tables():
    """Создает таблицы в базе данных SQLite."""
    Base.metadata.create_all(bind=engine)
    print("Database tables created/checked successfully.")


# Функция для получения сессии БД (зависимость FastAPI)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()