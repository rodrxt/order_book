import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

from src.utils.logger import setup_logger
from src.models.client import Client

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SQL_DIR = BASE_DIR / "src" / "sql"
DB_DIR = DATA_DIR / "trading.db"

class DataBaseManager:
    def __init__(self, db_path = None):
        self.logger = setup_logger("database")

        # Para poder configurar entorno de pruebas
        self.db_path = db_path or DB_DIR
        
        self._connection = None
        if self.db_path == ":memory:":
            self._connection = sqlite3.connect(":memory:", check_same_thread=False)
            self._connection.execute("PRAGMA foreign_keys = ON;")

        if self.db_path != ":memory:":
            os.makedirs(DATA_DIR, exist_ok=True)

        self._init_db()
    
    def get_connection(self):
        """
        Usamos un método privado para mayor seguridad. Solo lo podemos desde funciones internas
        """
        if self._connection:
            return self._connection
        
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        """
        Utilizo esta función para inicializar las tablas que vamos a usar
        """
        create_tables_sql = SQL_DIR / "create_tables.sql"

        try:
            conn = self.get_connection()
            with open(create_tables_sql, 'r') as f:
                create_orders_query = f.read()
            conn.executescript(create_orders_query)
            conn.commit()

            self.logger.info("Tables initialized")
        
        except Exception as e:
            self.logger.critical(f"Error while initializing tables: {e}")
            raise e
    
    @contextmanager
    def transaction(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()