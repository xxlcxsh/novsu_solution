// frontend/src/main.tsx

import React from 'react';
import ReactDOM from 'react-dom/client';
// Импортируем провайдер темы и CssBaseline из MUI
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import App from './App.tsx';
import './index.css'; 

// 1. Создание базовой темы (для согласованности)
// Мы используем светлую тему по умолчанию.
const theme = createTheme({
  palette: {
    background: {
      default: '#f5f5f5', // Устанавливаем светло-серый фон для всего тела
    },
  },
  typography: {
    fontFamily: [
      'Roboto', // Стандартный шрифт MUI
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {/* 2. Оборачиваем приложение в ThemeProvider */}
    <ThemeProvider theme={theme}>
      {/* 3. CssBaseline сбрасывает CSS браузера для лучшей согласованности */}
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>,
);