# Guía de Comandos de Memoria - Fase 1

## Comandos para Administrar Memoria Durante la Conversación

### Comandos de Visualización

#### `/memory_short`
Muestra todas las memorias a corto plazo actuales con:
- Número de interacción
- Fragmento del mensaje del usuario (primeros 50 caracteres)
- Fragmento de la respuesta del asistente (primeros 50 caracteres)
- Timestamp de la interacción

**Ejemplo de uso:**
```
> /memory_short

📝 Memorias a corto plazo (3 items):
  1. Usuario: Hola, ¿cómo estás?
     Asistente: ¡Hola! Estoy muy bien, gracias por preguntar...
     Tiempo: 2024-01-15 21:20:45

  2. Usuario: ¿Puedes ayudarme con Python?
     Asistente: ¡Por supuesto! Me encanta ayudar con Python...
     Tiempo: 2024-01-15 21:21:12
```

#### `/memory_count`
Muestra un resumen del estado actual de la memoria:
- Cantidad de interacciones en memoria a corto plazo
- Cantidad de memorias en memoria a largo plazo
- Límite configurado para auto-transición

**Ejemplo de uso:**
```
> /memory_count

📊 Estado de la memoria:
  📝 Corto plazo: 5 interacciones
  🧠 Largo plazo: 12 memorias
  🔄 Límite auto-transición: 10
```

### Comandos de Limpieza

#### `/clear_short`
Limpia únicamente las memorias a corto plazo, manteniendo las memorias a largo plazo intactas.

#### `/clear_long`
Limpia únicamente las memorias a largo plazo, manteniendo las memorias a corto plazo intactas.

#### `/clear`
Limpia tanto las memorias a corto plazo como a largo plazo.

### Comandos de Memoria a Largo Plazo

#### `/memory_list`
Muestra todas las memorias a largo plazo guardadas.

#### `/memory_delete <índice>`
Elimina una memoria específica a largo plazo por su índice.

## Funcionamiento del Sistema de Memoria

### Memoria a Corto Plazo
- Se almacenan automáticamente todas las interacciones usuario-asistente
- Se mantienen en memoria durante la sesión actual
- Se utilizan para proporcionar contexto inmediato al LLM
- Se auto-transicionan a largo plazo cuando se alcanza el límite configurado

### Memoria a Largo Plazo
- Almacena resúmenes de conversaciones importantes
- Persiste entre sesiones
- Se puede consultar para recuperar información relevante
- Se puede gestionar manualmente con comandos específicos

## Verificación del Funcionamiento

Para verificar que el sistema de memoria está funcionando correctamente:

1. **Inicia una conversación:**
   ```
   > Hola, me llamo Juan y me gusta la programación
   ```

2. **Verifica que se guardó en memoria a corto plazo:**
   ```
   > /memory_count
   > /memory_short
   ```

3. **Continúa la conversación y verifica el contexto:**
   ```
   > ¿Recuerdas mi nombre?
   ```

4. **Verifica el crecimiento de la memoria:**
   ```
   > /memory_count
   ```

El sistema debería recordar información de interacciones anteriores y mostrar el crecimiento en el contador de memorias a corto plazo.