import React from 'react';
import { 
    Box, 
    Button, 
    Divider, 
    Drawer, 
    List, 
    ListItemText, 
    ListItemIcon, 
    Typography, 
    IconButton,
    CircularProgress,
    // !!! ИСПРАВЛЕНИЕ: Используем ListItemButton вместо ListItem
    ListItemButton 
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import DeleteIcon from '@mui/icons-material/Delete';
import LogoutIcon from '@mui/icons-material/Logout';

// Интерфейс для данных чата, которые мы получаем от бэкенда
interface Chat {
    id: number;
    title: string;
    created_at: string;
}

interface SidebarProps {
    accessToken: string;
    chats: Chat[];
    currentChatId: number | null;
    isLoading: boolean;
    onSelectChat: (id: number) => void;
    onCreateNewChat: () => void;
    onDeleteChat: (id: number) => void;
    onLogout: () => void;
}

const API_URL = 'http://localhost:8000';

const Sidebar: React.FC<SidebarProps> = ({
    accessToken,
    chats,
    currentChatId,
    isLoading,
    onSelectChat,
    onCreateNewChat,
    onDeleteChat,
    onLogout
}) => {
    
    // Функция для обработки удаления чата с подтверждением
    const handleDelete = async (id: number) => {
        // 🛑 ИЗМЕНЕНИЕ: Заменяем window.confirm на простой вывод в консоль
        console.log(`Попытка удалить чат ID: ${id}. В реальном приложении здесь был бы модальный компонент.`);
        // Временно пропускаем подтверждение для функциональности в Immersive

        try {
            const response = await fetch(`${API_URL}/chats/${id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                },
            });
            
            if (response.status === 204) {
                // Если удаление успешно, вызываем функцию обновления списка
                onDeleteChat(id); 
            } else if (response.status === 401 || response.status === 403) {
                console.error("Ошибка 401/403: Нет прав или токен недействителен.");
                // Возможно, стоит вызвать onLogout() здесь, как и в App.tsx
            } else {
                throw new Error("Не удалось удалить чат.");
            }
        } catch (error) {
            console.error("Ошибка при удалении чата:", error);
        }
    };
    
    return (
        <Drawer
            variant="permanent"
            sx={{
                width: 260,
                flexShrink: 0,
                '& .MuiDrawer-paper': {
                    width: 260,
                    boxSizing: 'border-box',
                    bgcolor: '#2f3136',
                    color: '#fff',
                    p: 1,
                    // 🛑 ИЗМЕНЕНИЕ 1: Убираем скругление углов
                    borderRadius: 0, 
                    // 🛑 ИЗМЕНЕНИЕ 2: Фиксируем слева (если это не было сделано ранее)
                    left: 0, 
                },
            }}
        >
            <Box sx={{ p: 1, height: '100%', display: 'flex', flexDirection: 'column' }}>
                
                {/* Заголовок и кнопка нового чата */}
                <Typography variant="h6" sx={{ mb: 2, ml: 1, color: '#b9bbbe' }}>
                    Ваши Диалоги
                </Typography>
                <Button 
                    variant="contained" 
                    fullWidth 
                    startIcon={<AddIcon />} 
                    onClick={onCreateNewChat}
                    sx={{ mb: 2, bgcolor: '#b9bbbe', '&:hover': { bgcolor: '#5d626a' } }}
                >
                    Новый Чат
                </Button>

                <Divider sx={{ mb: 1, bgcolor: '#4f545c' }} />

                {/* Список чатов */}
                <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
                    {isLoading ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                            <CircularProgress size={24} color="inherit" />
                        </Box>
                    ) : (
                        <List dense>
                            {chats.map((chat) => (
                                // !!! ИСПРАВЛЕНИЕ ОШИБКИ: Используем ListItemButton !!!
                                <ListItemButton
                                    key={chat.id}
                                    selected={chat.id === currentChatId}
                                    onClick={() => onSelectChat(chat.id)}
                                    sx={{
                                        borderRadius: '8px',
                                        '&.Mui-selected': { 
                                            bgcolor: '#5d626a', 
                                            '&:hover': { bgcolor: '#5d626a' } 
                                        },
                                        '&:hover': { bgcolor: '#4f545c' }
                                    }}
                                >
                                    <ListItemIcon sx={{ minWidth: 35, color: 'inherit' }}>
                                        <ChatBubbleOutlineIcon fontSize="small" />
                                    </ListItemIcon>
                                    <ListItemText 
                                        primary={chat.title} 
                                        secondary={new Date(chat.created_at).toLocaleDateString()}
                                        primaryTypographyProps={{ 
                                            noWrap: true, 
                                            variant: 'body2', 
                                            fontWeight: 'bold' 
                                        }}
                                        secondaryTypographyProps={{ 
                                            color: '#b9bbbe', 
                                            variant: 'caption' 
                                        }}
                                    />
                                    <IconButton 
                                        edge="end" 
                                        aria-label="delete" 
                                        onClick={(e) => { e.stopPropagation(); handleDelete(chat.id); }}
                                        size="small"
                                        sx={{ ml: 1, color: '#b9bbbe', '&:hover': { color: '#f04747' } }}
                                    >
                                        <DeleteIcon fontSize="inherit" />
                                    </IconButton>
                                </ListItemButton>
                            ))}
                        </List>
                    )}
                </Box>
                
                {/* Футер: Кнопка Выхода */}
                <Divider sx={{ mt: 1, mb: 1, bgcolor: '#4f545c' }} />
                <Button 
                    variant="text" 
                    fullWidth 
                    startIcon={<LogoutIcon />} 
                    onClick={onLogout}
                    sx={{ color: '#f04747', justifyContent: 'flex-start', p: 1, '&:hover': { bgcolor: '#4f545c' } }}
                >
                    Выход
                </Button>
            </Box>
        </Drawer>
    );
};

export default Sidebar;