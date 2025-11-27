from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound
# Обновленные импорты согласно вашему запросу
import database, schemas
from datetime import datetime
from typing import List, Optional

# --- Функции для Чатов (Chat) ---

def create_user_chat(db: Session, user_id: int, title: str = "Новый чат") -> database.Chat:
    """Создает новый чат для пользователя."""
    # Используем 'owner_id' (как в предыдущих версиях) или 'user_id' в зависимости от вашей модели
    # Если в database.py поле называется owner_id, используйте owner_id=user_id
    db_chat = database.Chat(user_id=user_id, title=title) 
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat

def get_user_chats(db: Session, user_id: int) -> List[database.Chat]:
    """Получает все чаты для данного пользователя, отсортированные по дате."""
    # Используем 'owner_id' (как в предыдущих версиях) или 'user_id' в зависимости от вашей модели
    return db.query(database.Chat).filter(database.Chat.user_id == user_id).order_by(database.Chat.created_at.desc()).all()

def get_chat_owner_id(db: Session, chat_id: int) -> Optional[int]:
    """Возвращает ID владельца чата."""
    chat = db.query(database.Chat).filter(database.Chat.id == chat_id).first()
    # Предполагаем, что поле владельца в модели Chat называется owner_id или user_id
    return chat.user_id if chat else None 

def delete_chat(db: Session, chat_id: int):
    """Удаляет чат и все связанные сообщения."""
    # ДОБАВЛЕНО: Удаление сообщений, как в предыдущей, более надежной версии
    db.query(database.Message).filter(database.Message.chat_id == chat_id).delete()
    db.query(database.Chat).filter(database.Chat.id == chat_id).delete()
    db.commit()
    # Возвращаем True, если успешно удалено, как в вашем примере
    return True 

def update_chat_title(db: Session, chat_id: int, new_title: str) -> Optional[database.Chat]:
    """Обновляет заголовок чата по его ID."""
    db_chat = db.query(database.Chat).filter(database.Chat.id == chat_id).first()
    if db_chat:
        db_chat.title = new_title
        db.commit()
        db.refresh(db_chat)
        return db_chat
    return None

def get_message_count_by_chat_id(db: Session, chat_id: int) -> int:
    """Возвращает количество сообщений в чате."""
    return db.query(database.Message).filter(database.Message.chat_id == chat_id).count()

# --- Функции для Сообщений (Message) ---

def get_messages_by_chat_id(db: Session, chat_id: int) -> List[database.Message]:
    """Получает все сообщения для данного чата."""
    # Используем created_at (как в предыдущих версиях) или timestamp в зависимости от вашей модели
    return db.query(database.Message).filter(database.Message.chat_id == chat_id).order_by(database.Message.created_at.asc()).all()

def create_message(
    db: Session, 
    chat_id: int, 
    content: str, 
    sender: str, 
    # НОВЫЙ АРГУМЕНТ: для хранения JSON-строки источников (TEXT поле в БД)
    source_documents_json: Optional[str] = None
) -> database.Message:
    """Создает и сохраняет новое сообщение, включая источники RAG (если есть)."""
    
    db_message = database.Message(
        chat_id=chat_id, 
        content=content, 
        sender=sender,
        # Используем created_at (как в предыдущих версиях) или timestamp в зависимости от вашей модели
        created_at=datetime.utcnow(), 
        source_documents_json=source_documents_json # Сохранение JSON
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message