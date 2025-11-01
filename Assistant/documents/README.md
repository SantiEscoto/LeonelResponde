# Documentos para la Base de Conocimiento

Esta carpeta contiene los documentos que se procesarán para la base de conocimiento del asistente.

## Estructura:
- `pdfs/` - Documentos PDF
- `texts/` - Documentos de texto (TXT, MD)

## Cómo usar:
1. Coloca tus documentos PDF en la carpeta `pdfs/`
2. Coloca tus documentos de texto en la carpeta `texts/`
3. Ejecuta el asistente con: `python3 main.py --ui pyside6`
4. Los documentos se procesarán automáticamente

## Formatos soportados:
- PDF (.pdf)
- Texto (.txt)
- Markdown (.md)
- JSON (.json)

## Notas:
- Los PDFs se procesan automáticamente al iniciar el asistente
- Los documentos grandes se dividen en chunks
- Se mantiene un índice de búsqueda para consultas rápidas
