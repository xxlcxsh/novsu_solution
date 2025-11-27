import React, { useState, useEffect } from 'react';
import Chat from './Chat'; 
import Auth from './Auth';
import Sidebar from './Sidebar'; // Импортируем новый компонент Sidebar
import { Box, CssBaseline, ThemeProvider, createTheme, Typography } from '@mui/material';

// Интерфейс для данных чата
interface ChatType {
    id: number;
    title: string;
    created_at: string;
}

// URL для FastAPI
const API_URL = 'http://localhost:8000';

// Создание базовой темы MUI
const theme = createTheme({
  palette: {
    primary: {
      main: '#42a5f5', // Синий для сообщений пользователя
    },
    background: {
      default: '#f5f5f5',
    },
  },
  components: {
    MuiPaper: {
        styleOverrides: {
            root: {
                // 🛑 ИЗМЕНЕНИЕ: УДАЛИТЬ СТРОКУ borderRadius: '8px', 
                // чтобы убрать скругление для всех компонентов на странице, включая основной чат
            }
        }
    }
  }
});


function App() {
  const [token, setToken] = useState<string | null>(null);
  const [chats, setChats] = useState<ChatType[]>([]);
  const [currentChatId, setCurrentChatId] = useState<number | null>(null);
  const [isLoadingChats, setIsLoadingChats] = useState(false);

  // --- Функции Управления Токеном и Входом ---

  useEffect(() => {
    const savedToken = localStorage.getItem('accessToken');
    if (savedToken) {
      setToken(savedToken);
    }
  }, []);

  const handleLogin = (newToken: string) => {
    setToken(newToken);
    localStorage.setItem('accessToken', newToken);
  };
  
  const handleLogout = () => {
    setToken(null);
    setCurrentChatId(null);
    setChats([]);
    localStorage.removeItem('accessToken');
  };
  
  // --- Функции для Работы с Чатами ---

  const fetchChats = async (authToken: string) => {
    setIsLoadingChats(true);
    try {
        const response = await fetch(`${API_URL}/chats/`, {
            headers: {
                'Authorization': `Bearer ${authToken}`,
            },
        });

        if (!response.ok) {
            throw new Error('Не удалось загрузить список чатов');
        }

        const data: ChatType[] = await response.json();
        setChats(data);
        
        // Если нет выбранного чата, выбираем первый или создаем новый
        if (data.length > 0 && currentChatId === null) {
            setCurrentChatId(data[0].id);
        } else if (data.length === 0) {
             // Автоматическое создание первого чата, если нет ни одного
             handleCreateNewChat();
        }

    } catch (error) {
        console.error('Ошибка при загрузке чатов:', error);
        // В случае ошибки, возможно, токен устарел
        if ((error as Error).message.includes('401')) {
             handleLogout();
        }
    } finally {
        setIsLoadingChats(false);
    }
  };
  
  const handleCreateNewChat = async () => { 
    // Обязательная проверка, что токен существует
    const authToken = token;
    if (!authToken) {
        console.error("Попытка создать чат без токена.");
        // Можно добавить handleLogout() или просто вернуть управление
        return; 
    }

    try {
        const response = await fetch(`${API_URL}/chats/`, {
            method: 'POST',
            headers: {
                // Используем проверенный authToken
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json', // Добавил Content-Type для POST
            },
            body: JSON.stringify({ title: "Новый чат" }) // Добавил тело запроса, так как POST
        });
        
        if (!response.ok) throw new Error('Не удалось создать чат');
        
        const newChat: ChatType = await response.json();
        setChats(prev => [newChat, ...prev]);
        setCurrentChatId(newChat.id);

    } catch (error) {
        console.error("Ошибка при создании чата:", error);
    }
};


  const handleDeleteChat = (deletedId: number) => {
      setChats(prev => prev.filter(chat => chat.id !== deletedId));
      
      // Если удаленный чат был текущим, выбираем первый оставшийся
      setChats(prevChats => {
        const remainingChats = prevChats.filter(chat => chat.id !== deletedId);
        
        if (deletedId === currentChatId) {
            if (remainingChats.length > 0) {
                setCurrentChatId(remainingChats[0].id);
            } else {
                // Если чатов не осталось, создаем новый
                setCurrentChatId(null); // Устанавливаем null, чтобы избежать ошибки
                handleCreateNewChat();
            }
        }
        return remainingChats;
      });
  };

  // Эффект для загрузки чатов после входа
  useEffect(() => {
    if (token) {
      fetchChats(token);
    }
  }, [token]);


  if (!token) {
    return (
        <Box
            sx={{
                height: "100vh",
                width: "100vw",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                backgroundColor: "#f5f5f5",
            }}
        >
            <Auth onLogin={handleLogin} />
        </Box>
    );
  }


  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', height: '100vh', width: '100vw' }}> {/* Установим 100vw для уверенности */}
        {/* Боковая панель */}
        <Sidebar
            accessToken={token}
            chats={chats}
            currentChatId={currentChatId}
            isLoading={isLoadingChats}
            onSelectChat={setCurrentChatId}
            onCreateNewChat={handleCreateNewChat}
            onDeleteChat={handleDeleteChat}
            onLogout={handleLogout}
        />
        
        {/* Основная область чата */}
        <Box 
            component="main" 
            sx={{ 
                flexGrow: 1, 
                height: '100%',
                // 🛑 ФИКС: Сдвигаем основной контент вправо, чтобы он начинался после сайдбара 
                // 🛑 ФИКС: Предотвращает переполнение
                minWidth: 0, 
            }}
        >
            {currentChatId !== null ? (
                 <Chat 
                    accessToken={token} 
                    chatId={currentChatId} 
                    onLogout={handleLogout}
                 />
            ) : (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                    <Typography variant="h5" color="text.secondary">
                        Создайте новый чат для начала работы.
                    </Typography>
                </Box>
            )}
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;