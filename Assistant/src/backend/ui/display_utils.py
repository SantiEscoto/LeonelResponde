"""
Display utilities for consistent UI formatting and error handling.
"""

def _get_config():
    """Lazy import of config to avoid circular imports"""
    from src.backend.utils.unified_config import get_config
    return get_config()


def display_component_status(component, component_name: str, icon: str, status_func, error_message: str):
    """Helper function to display component status with consistent formatting"""
    if component:
        try:
            status = status_func()
            print(f"{icon} {component_name}:")
            return status
        except Exception as e:
            from src.backend.utils.unified_logger import get_unified_logger
            logger = get_unified_logger("DisplayUtils")
            logger.error(f"Error obteniendo estado de {component_name}: {e}")
            print(f"{icon} {component_name}: {error_message}")
            return None
    else:
        print(f"{icon} {component_name}: No disponible")
        return None


def display_section_header(title: str, separator: str = None):
    """Display section headers consistently"""
    if separator is None:
        config = _get_config()
        separator = config.ui.sub_separator_line
    print(f"\n{title}\n{separator}")


def display_status_item(label: str, value, unit: str = ""):
    """Display status items with consistent formatting"""
    print(f"  - {label}: {value}{unit}")


def display_success_error(success: bool, component_name: str, action: str):
    """Display success/error messages consistently"""
    icon, status = ("✅", action) if success else ("❌", "Error")
    print(f"   {icon} {component_name}: {status}")


def display_error_with_help(error_msg: str, help_text: str = None, details: str = None):
    """Display error messages with optional help and details"""
    messages = [f"\n❌ Error: {error_msg}"]
    if details:
        messages.append(f"   🔍 Detalles: {details}")
    if help_text:
        messages.append(f"   💡 {help_text}")
    print("\n".join(messages))


def display_validation_error(error, context: str = "entrada"):
    """Display validation error with context"""
    print(
        (
            "❌ Error de validación en {context}: {error}\n"
            "   💡 Verifica que el texto no contenga caracteres especiales "
            "o sea demasiado largo"
        ).format(context=context, error=error)
    )


def display_index_error(index: int, max_range: int, command_name: str):
    """Display index out of range error with helpful information"""
    print(
        (
            "\n❌ Error: Índice {idx} fuera de rango\n"
            "   📊 Rango válido: 1-{max_range}\n"
            "   💡 Uso correcto: {cmd} [número entre 1 y {max_range}]"
        ).format(idx=index + 1, max_range=max_range, cmd=command_name)
    )


def display_component_unavailable_error(component_name: str, suggestion: str = None):
    """Display component unavailable error with suggestion"""
    msg = f"\n❌ Error: {component_name} no disponible"
    if suggestion:
        msg += f"\n   💡 {suggestion}"
    else:
        msg += "\n   💡 Verifica que el sistema esté correctamente inicializado"
    print(msg)


def display_available_commands():
    """Display available commands in an organized format."""
    print("🔧 SISTEMA:")
    print("  /help        - Mostrar esta ayuda")
    print("  /salir       - Salir del programa")
    print("  /status      - Ver estado de todos los componentes")
    print("  /resources   - Ver información detallada de recursos")
    print("\n💾 MEMORIA:")
    print("  /clear       - Limpiar toda la memoria")
    print("  /memory      - Ver estado de la memoria")
    print("  /list_short  - Ver interacciones de memoria a corto plazo")
    print("  /list_long   - Ver interacciones de memoria a largo plazo")
    print("  /delete_short [índice] - Borrar interacción específica (corto plazo)")
    print("  /delete_long [índice]  - Borrar interacción específica (largo plazo)")
    print("\n📚 CONOCIMIENTO:")
    print("  /rag on|off  - Activar/desactivar búsqueda RAG")
    print("  /add <texto> - Agregar texto a la base de conocimiento")

