// frontend/src/Auth.tsx

import React, { useState } from 'react';
import { Box, Button, TextField, Typography, Container, Paper } from '@mui/material';

const AUTH_URL = 'http://localhost:8000';

interface AuthProps {
    onLogin: (token: string) => void;
}

const Auth: React.FC<AuthProps> = ({ onLogin }) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [isRegistering, setIsRegistering] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async () => {
        setError('');
        const endpoint = isRegistering ? '/register' : '/token';
        
        try {
            const response = await fetch(`${AUTH_URL}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });

            const data = await response.json();

            if (!response.ok) {
                setError(data.detail || "Ошибка авторизации");
                return;
            }
            
            // Успешный вход/регистрация, получаем токен
            const token = data.access_token;
            localStorage.setItem('accessToken', token);
            onLogin(token); 

        } catch (e) {
            setError("Ошибка сети. Проверьте бэкенд FastAPI.");
        }
    };

    return (
        <Container component="main" maxWidth="xs" sx={{ mt: 8 }}>
            <Paper elevation={3} sx={{ p: 4, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography component="h1" variant="h5">
                    {isRegistering ? 'Регистрация' : 'Вход'}
                </Typography>
                <Box component="form" onSubmit={(e) => { e.preventDefault(); handleSubmit(); }} sx={{ mt: 1 }}>
                    <TextField
                        margin="normal"
                        required
                        fullWidth
                        label="Имя пользователя"
                        autoFocus
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                    />
                    <TextField
                        margin="normal"
                        required
                        fullWidth
                        label="Пароль"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                    />
                    {error && <Typography color="error" variant="body2" sx={{ mt: 1 }}>{error}</Typography>}
                    
                    <Button
                        type="submit"
                        fullWidth
                        variant="contained"
                        sx={{ mt: 3, mb: 2 }}
                    >
                        {isRegistering ? 'Зарегистрироваться' : 'Войти'}
                    </Button>
                    
                    <Button
                        fullWidth
                        onClick={() => setIsRegistering(!isRegistering)}
                        variant="text"
                    >
                        {isRegistering ? 'Уже есть аккаунт? Войти' : 'Нет аккаунта? Зарегистрироваться'}
                    </Button>
                </Box>
            </Paper>
        </Container>
    );
};

export default Auth;