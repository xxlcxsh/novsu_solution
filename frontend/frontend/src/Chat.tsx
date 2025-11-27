import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
    Box,
    TextField,
    Button,
    Paper,
    Typography,
    CircularProgress,
    Avatar,
    Switch, // Добавлен импорт Switch
    FormControlLabel, // Добавлен импорт FormControlLabel
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import { ChevronDown, ChevronRight, FileText } from 'lucide-react'; 

interface SourceDocument {
    filepath: string;
    content: string;
}

interface Message {
    id: number | string; 
    content: string; 
    sender: 'user' | 'ai';
    timestamp?: string; 
    source_documents?: SourceDocument[] | null;
}

interface ChatProps {
    accessToken: string;
    chatId: number; 
    onLogout: () => void;
}

const API_URL = 'http://localhost:8000'; 

const SourceDisplay: React.FC<{ sources: SourceDocument[] }> = ({ sources }) => {
    const [isContextVisible, setIsContextVisible] = useState(false);

    return (
        <Box sx={{ mt: 1, p: 1.5, bgcolor: '#f0f4f8', borderTop: '1px solid #e0e0e0', borderRadius: '0 0 8px 8px', maxWidth: '100%', overflow: 'hidden' }}>
            <Box 
                sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', mb: isContextVisible ? 1.5 : 0 }} 
                onClick={() => setIsContextVisible(!isContextVisible)}
            >
                <Typography variant="caption" fontWeight="medium" color="text.secondary" sx={{ display: 'flex', alignItems: 'center' }}>
                    <FileText size={14} style={{ marginRight: 4 }} />
                    {isContextVisible ? "Скрыть источники" : `Показать ${sources.length} источник(ов)`}
                </Typography>
                {isContextVisible ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </Box>

            {isContextVisible && (
                <Box sx={{ mt: 1, maxHeight: 200, overflowY: 'auto' }}>
                    {sources.map((source, index) => {
                        const fileName = source.filepath.split('/').pop(); // оригинальное имя с расширением
                        // const fileUrl = `/files/${fileName}`; // путь на бекенд к файлу (уже не нужен, используем прямую ссылку)
                        return (
                            <Paper key={index} elevation={0} sx={{ p: 1.5, mb: 1, bgcolor: 'white', borderLeft: '3px solid #1976d2' }}>
                                <Typography variant="caption" color="text.primary" fontWeight="bold" sx={{ mb: 0.5, display: 'block' }}>
                                    Источник: <a href={`http://localhost:8000/files/${fileName}`} target="_blank" rel="noopener noreferrer">{fileName}</a>
                                </Typography>
                                <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic', fontSize: '0.65rem' }}>
                                    {source.content}
                                </Typography>
                            </Paper>
                        );
                    })}
                </Box>
            )}
        </Box>
    );
};


const Chat: React.FC<ChatProps> = ({ accessToken, chatId, onLogout }) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    // НОВОЕ СОСТОЯНИЕ: для переключателя таблиц
    const [useTables, setUseTables] = useState(false); 
    
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const fetchHistory = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await fetch(`${API_URL}/chats/${chatId}/messages`, {
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                },
            });
            if (!response.ok) throw new Error('Ошибка загрузки истории чата');
            const data: Message[] = await response.json();
            setMessages(data);
        } catch (error) {
            console.error('Ошибка при загрузке истории:', error);
        } finally {
            setIsLoading(false);
        }
    }, [chatId, accessToken]);

    useEffect(() => {
        if (chatId !== null) fetchHistory();
    }, [chatId, fetchHistory]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userQuery = input;
        const userMessage: Message = { id: Date.now().toString() + '-user', content: userQuery, sender: 'user' };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        const aiMessagePlaceholderId = Date.now().toString() + '-ai-placeholder';
        setMessages(prev => [...prev, { id: aiMessagePlaceholderId, content: '...', sender: 'ai' }]);

        try {
            const response = await fetch(`${API_URL}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                },
                body: JSON.stringify({
                    chat_id: chatId,
                    query: userQuery,
                    use_tables: useTables, // <--- ОТПРАВЛЯЕМ НОВЫЙ ФЛАГ
                })
            });
            if (!response.ok) throw new Error('Server error');
            const data = await response.json();

            const aiMessage: Message = {
                id: Date.now().toString() + '-ai',
                content: data.content,
                sender: 'ai',
                source_documents: data.source_documents ?? []
            };

            setMessages(prev => {
                const ix = prev.findIndex(m => m.id === aiMessagePlaceholderId);
                if (ix !== -1) {
                    const arr = [...prev];
                    arr[ix] = aiMessage;
                    return arr;
                }
                return prev;
            });

        } catch (error) {
            console.error('API error:', error);
            setMessages(prev => [
                ...prev.filter(m => m.id !== aiMessagePlaceholderId),
                { id: Date.now(), content: 'Ошибка сервера RAG.', sender: 'ai' }
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    if (isLoading && messages.length === 0) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', bgcolor: '#f5f5f5' }}>
            <Box component="header" sx={{ p: 2, borderBottom: '1px solid #e0e0e0', bgcolor: 'white', boxShadow: 1 }}>
                <Box sx={{ textAlign: 'center' }}> 
                    <Typography variant="h6" color="text.secondary">
                        Чат ID: {chatId}
                    </Typography>
                </Box>
            </Box>

            <Box
                component="main"
                sx={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    minHeight: 0,
                    px: 3,
                    pt: 4,
                    pb: 12,
                }}
            >
                <Box
                    sx={{
                        flex: 1,
                        overflowY: 'auto',
                        pr: 1,
                        minHeight: 0,
                        display: 'flex',
                        flexDirection: 'column',
                    }}
                >
                    <Box>
                        {messages.length === 0 && !isLoading && (
                            <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <Typography variant="h6" color="text.disabled">
                                    Начните диалог в чате #{chatId}...
                                </Typography>
                            </Box>
                        )}
                        {messages.map((msg) => (
                            <Box key={msg.id} sx={{ display: 'flex', flexDirection: 'column', alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start', mb: 3 }}>
                                <Box sx={{ display: 'flex', justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start', width: '100%' }}>
                                    {msg.sender === 'ai' && <Avatar sx={{ width: 32, height: 32, mr: 1, bgcolor: 'teal' }}>AI</Avatar>}
                                    <Paper sx={{ 
                                        p: 2, maxWidth: '80%', bgcolor: msg.sender === 'user' ? 'primary.main' : 'white',
                                        color: msg.sender === 'user' ? 'white' : 'text.primary',
                                        boxShadow: 2,
                                        borderRadius: '12px',
                                        borderTopLeftRadius: msg.sender === 'user' ? '12px' : '4px',
                                        borderTopRightRadius: msg.sender === 'user' ? '4px' : '12px',
                                        borderBottomLeftRadius: (msg.sender === 'ai' && msg.source_documents) ? '0px' : '12px',
                                        borderBottomRightRadius: (msg.sender === 'user' || !msg.source_documents) ? '12px' : '0px',
                                    }}>
                                        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>{msg.content}</Typography>
                                    </Paper>
                                    {msg.sender === 'user' && <Avatar sx={{ width: 32, height: 32, ml: 1, bgcolor: 'grey.700' }}>Я</Avatar>}
                                </Box>
                                {msg.sender === 'ai' && msg.source_documents && msg.source_documents.length > 0 && (
                                    <Box sx={{ maxWidth: '80%', ml: '40px', width: '100%' }}> 
                                        <SourceDisplay sources={msg.source_documents} />
                                    </Box>
                                )}
                            </Box>
                        ))}
                        <Box ref={messagesEndRef} />
                    </Box>
                </Box>
            </Box>

            <Box component="footer" sx={{ p: 2, borderTop: '1px solid #e0e0e0', bgcolor: 'white' }}>
                
                {/* НОВЫЙ ЭЛЕМЕНТ: Переключатель для гибридного RAG */}
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', px: 3, pb: 1 }}>
                    <FormControlLabel
                        control={
                            <Switch
                                checked={useTables}
                                onChange={(e) => setUseTables(e.target.checked)}
                                name="useTables"
                                color="primary"
                            />
                        }
                        label="Искать в таблицах (гибридный RAG)"
                    />
                </Box>
                
                <Box sx={{ display: 'flex', gap: 1, px: 3 }}>
                    <TextField
                        fullWidth multiline rows={1} maxRows={6} placeholder={isLoading ? 'Ожидание ответа...' : 'Напишите сообщение...'}
                        value={input} onChange={(e) => setInput(e.target.value)}
                        onKeyPress={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                        disabled={isLoading} variant="outlined"
                        sx={{ '& .MuiOutlinedInput-root': { borderRadius: '25px', padding: '8px 14px' }, '& textarea': { resize: 'vertical' } }}
                    />
                    <Button variant="contained" onClick={handleSend} disabled={isLoading || !input.trim()} sx={{ borderRadius: '25px', minWidth: 'auto', width: '50px', height: '50px', p: 0 }}>
                        {isLoading ? <CircularProgress size={24} color="inherit" /> : <SendIcon />}
                    </Button>
                </Box>
            </Box>
        </Box>
    );
};

export default Chat;