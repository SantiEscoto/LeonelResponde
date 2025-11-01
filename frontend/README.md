# 🚀 Leonel Responde - Frontend

Frontend moderno para el asistente de IA offline Leonel Responde, construido con React, TypeScript y Tailwind CSS.

## ✨ Características

- **💬 Chat Interface Moderna** - Interfaz de chat intuitiva y responsive
- **🌙 Dark/Light Mode** - Temas personalizables con detección automática del sistema
- **⚡ Real-time Communication** - WebSocket para comunicación en tiempo real
- **📱 Responsive Design** - Funciona perfectamente en desktop y móvil
- **🎨 Modern UI** - Diseño moderno con Tailwind CSS
- **🔒 Type Safety** - TypeScript para código robusto
- **📊 State Management** - Zustand para gestión de estado
- **🧪 Testing Ready** - Configurado para testing con Vitest

## 🛠️ Stack Tecnológico

- **React 18** - Framework principal
- **TypeScript** - Type safety
- **Vite** - Build tool moderno
- **Tailwind CSS** - Styling
- **Zustand** - State management
- **Axios** - HTTP client
- **Socket.io** - WebSocket communication

## 🚀 Instalación y Desarrollo

### Prerrequisitos

- Node.js 18+ (recomendado 20+)
- npm o yarn

### Instalación

```bash
# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev
```

### Scripts Disponibles

```bash
# Desarrollo
npm run dev          # Servidor de desarrollo
npm run build        # Build de producción
npm run preview      # Preview del build

# Testing
npm run test         # Ejecutar tests
npm run test:ui      # UI de testing
npm run test:coverage # Coverage de tests

# Utilidades
npm run lint         # Linting
npm run type-check   # Verificación de tipos
npm run clean        # Limpiar archivos temporales
```

## 📁 Estructura del Proyecto

```
src/
├── components/          # Componentes React
│   ├── ChatInterface.tsx
│   ├── MessageBubble.tsx
│   ├── InputField.tsx
│   ├── StatusIndicator.tsx
│   └── Header.tsx
├── store/              # Estado global (Zustand)
│   ├── chatStore.ts
│   └── settingsStore.ts
├── services/           # Servicios y APIs
│   ├── api.ts
│   └── websocket.ts
├── types/              # Tipos TypeScript
│   └── index.ts
├── hooks/              # Custom hooks
├── utils/              # Utilidades
├── App.tsx             # Componente principal
└── main.tsx            # Punto de entrada
```

## 🔧 Configuración

### Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# API Configuration
VITE_API_URL=http://localhost:8000
VITE_WS_URL=http://localhost:8000

# App Configuration
VITE_APP_NAME=Leonel Responde
VITE_APP_VERSION=1.0.0

# Development
VITE_DEBUG=true
```

### Configuración de Vite

El proyecto está configurado con:
- Proxy para API backend
- Alias de rutas (@/ para src/)
- Build optimizado con chunks manuales
- Source maps para debugging

## 🎨 Temas y Personalización

### Temas Disponibles

- **Light** - Tema claro
- **Dark** - Tema oscuro  
- **System** - Sigue la preferencia del sistema

### Personalización de Colores

Los colores se pueden personalizar en `tailwind.config.js`:

```javascript
theme: {
  extend: {
    colors: {
      primary: {
        // Colores primarios personalizados
      }
    }
  }
}
```

## 📱 Responsive Design

El frontend está optimizado para:
- **Desktop** - Experiencia completa
- **Tablet** - Adaptación de layout
- **Mobile** - Interfaz táctil optimizada

## 🔌 Integración con Backend

### API Endpoints

- `POST /query` - Enviar mensaje al asistente
- `POST /clear-memory` - Limpiar memoria
- `POST /add-document` - Agregar documento
- `GET /status` - Estado del sistema

### WebSocket Events

- `connect` - Conexión establecida
- `disconnect` - Conexión perdida
- `message` - Mensaje recibido
- `status` - Actualización de estado

## 🧪 Testing

### Configuración de Tests

```bash
# Instalar dependencias de testing
npm install -D vitest @testing-library/react @testing-library/jest-dom

# Ejecutar tests
npm run test
```

### Estructura de Tests

```
src/
├── components/
│   └── __tests__/
│       ├── ChatInterface.test.tsx
│       ├── MessageBubble.test.tsx
│       └── InputField.test.tsx
├── services/
│   └── __tests__/
│       ├── api.test.ts
│       └── websocket.test.ts
└── store/
    └── __tests__/
        ├── chatStore.test.ts
        └── settingsStore.test.ts
```

## 🚀 Deployment

### Build de Producción

```bash
# Build optimizado
npm run build

# Preview del build
npm run preview
```

### Variables de Entorno para Producción

```env
VITE_API_URL=https://api.leonelresponde.com
VITE_WS_URL=https://api.leonelresponde.com
VITE_DEBUG=false
```

## 📊 Performance

### Optimizaciones Implementadas

- **Code Splitting** - Carga lazy de componentes
- **Bundle Optimization** - Chunks manuales
- **Tree Shaking** - Eliminación de código no usado
- **Image Optimization** - Optimización de assets
- **Caching** - Headers de cache apropiados

### Métricas de Rendimiento

- **First Contentful Paint** < 1.5s
- **Largest Contentful Paint** < 2.5s
- **Cumulative Layout Shift** < 0.1
- **Time to Interactive** < 3.0s

## 🔒 Seguridad

### Medidas Implementadas

- **Content Security Policy** - Headers de seguridad
- **XSS Protection** - Sanitización de inputs
- **CSRF Protection** - Tokens de seguridad
- **Secure Headers** - Headers de seguridad

## 📈 Monitoreo

### Métricas Disponibles

- **Performance** - Core Web Vitals
- **Errors** - JavaScript errors
- **User Experience** - Métricas de uso
- **API Performance** - Tiempo de respuesta

## 🤝 Contribución

### Guías de Desarrollo

1. **Fork** el repositorio
2. **Crear** branch para feature
3. **Desarrollar** con tests
4. **Commit** con mensajes claros
5. **Push** y crear Pull Request

### Estándares de Código

- **ESLint** - Linting automático
- **Prettier** - Formateo de código
- **TypeScript** - Type safety
- **Testing** - Cobertura mínima 80%

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver `LICENSE` para más detalles.

## 🆘 Soporte

Para soporte técnico o preguntas:

- **Issues** - GitHub Issues
- **Discussions** - GitHub Discussions
- **Email** - soporte@leonelresponde.com

---

**Desarrollado con ❤️ para Leonel Responde**