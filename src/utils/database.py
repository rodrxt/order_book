import sqlite3
import os
from pathlib import Path

from src.utils.logger import setup_logger

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SQL_DIR = BASE_DIR / "src" / "sql"
DB_DIR = DATA_DIR / "trading.db"

def init_db():
    """
    Utilizo esta función para inicializar las tablas que vamos a usar
    """
    log = setup_logger("DATABASE")

    if not os.path.exists(DATA_DIR):
        log.debug("Tables do not exist yet. Starting creation.")
        os.makedirs(DATA_DIR)
    else:
        log.info("Tables already exist")
        return 1

    # Conexión para las órdenes
    conn = sqlite3.connect(DB_DIR)
    
    cursor = conn.cursor()

    # Usamos esto para habilitar las foreign keys en las tablas
    cursor.execute("PRAGMA foreign_keys = ON;")

    create_tables_sql = SQL_DIR / "create_tables.sql"

    try:
        with open(create_tables_sql, 'r') as f:
            create_orders_query = f.read()
        cursor.executescript(create_orders_query)
        conn.commit()

        log.info("Tables created")

    except Exception as e:
        log.error(f"Tables not created: {e}")
        raise Exception()
    
    finally:
        conn.close()