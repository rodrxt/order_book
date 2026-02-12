import logging
import sys
from pathlib import Path

def setup_logger(logger_name = "TradingLogs"):
    """
    Utilizamos un logger que nos permita almacenar todos los eventos relevantes en 
    un fichero de texto
    """

    # ./logs
    log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"{logger_name}.log"

    logger = logging.getLogger(logger_name)

    if not logger.handlers:
        # Nivel más bajo que queremos guardar
        logger.setLevel(logging.DEBUG)

        # Formato de los logs
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )

        # Para mostrar por consola
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        # Por consola solo mostramos los más importantes
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

        # Para almacenar el fichero
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        # En el fichero almacenamos todo
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    
    return logger