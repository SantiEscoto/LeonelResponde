# Standard library imports
import logging
from pathlib import Path
import sys

# Third-party imports
from colorama import Fore, Style, init

# Inicializar colorama
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Formatter con colores para la consola"""

    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA + Style.BRIGHT,
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, Fore.WHITE)
        record.levelname = f"{log_color}{record.levelname}{Style.RESET_ALL}"
        record.name = f"{Fore.BLUE}{record.name}{Style.RESET_ALL}"
        return super().format(record)


def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """
    Configura un logger con salida a consola y archivo
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Evitar duplicar handlers
    if logger.handlers:
        return logger

    # Formatter para archivos
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Formatter para consola con colores
    console_formatter = ColoredFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%H:%M:%S"
    )

    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Handler para archivo si se especifica
    if log_file:
        try:
            # Obtener directorio de logs
            current_dir = Path(__file__).parent.parent.parent
            logs_dir = current_dir / "logs"
            logs_dir.mkdir(exist_ok=True)

            file_path = logs_dir / log_file
            file_handler = logging.FileHandler(file_path, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"⚠️ No se pudo crear log file: {e}")

    return logger


# ✅ INSTANCIAS GLOBALES QUE FALTAN
def get_logger(name: str) -> logging.Logger:
    """Obtiene un logger para un módulo específico"""
    return setup_logger(name, f"{name.lower()}.log")


# ✅ ESTA LÍNEA FALTABA - Logger principal del sistema
system_logger = setup_logger("SYSTEM", "system.log")

# Test de importación
if __name__ == "__main__":
    print("🧪 Testing logger...")
    test_logger = get_logger("TEST")
    test_logger.info("✅ Logger funcionando correctamente")
    system_logger.info("✅ System logger funcionando")
    print("✅ Logger test completado")
