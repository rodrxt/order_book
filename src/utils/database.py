import sqlite3
import os
from pathlib import Path

from src.utils.logger import setup_logger
from src.models.client import Client

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SQL_DIR = BASE_DIR / "src" / "sql"
DB_DIR = DATA_DIR / "trading.db"

class DataBaseManager:
    def __init__(self):
        self.logger = setup_logger("DATABASE")

        if not os.path.exists(DATA_DIR):
            self.logger.debug("Data folder does not exist yet. Starting creation.")
        
        os.makedirs(DATA_DIR, exist_ok=True)
    
    def _get_connection(self):
        """
        Usamos un método privado para mayor seguridad. Solo lo podemos desde funciones internas
        """
        conn = sqlite3.connect(DB_DIR)

        # Usamos esto para habilitar las foreign keys en las tablas
        conn.execute("PRAGMA foreign_keys = ON;")

        return conn

    def init_db(self):
        """
        Utilizo esta función para inicializar las tablas que vamos a usar
        """
        create_tables_sql = SQL_DIR / "create_tables.sql"
        conn = self._get_connection()
        try:
            with open(create_tables_sql, 'r') as f:
                create_orders_query = f.read()
            conn.executescript(create_orders_query)
            conn.commit()

            self.logger.info("Tables initialized")

        except Exception as e:
            self.logger.error(f"Error while initializing tables: {e}")
            raise
        
        finally:
            conn.close()

    def add_new_client(self, client_data):
        """
        Usamos esta función para añadir un cliente a la db
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO clients (client_name, email) VALUES (?, ?)",
                (client_data.client_name, client_data.email)
            )
            # guardamos el id del usuario creado
            client_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO portfolios (client_id, asset_id, quantity) VALUES (?, ?, ?)",
                (client_id, 'CASH', 0.0)
            )
            
            conn.commit()
            self.logger.info(f"Client {client_id}: {client_data.client_name} created successfully")
            
            return client_id
        
        except sqlite3.IntegrityError as e:
            # Si algo falla, volvemos al estado previo
            conn.rollback()
            self.logger.error(f"Integrity error while creating new client: {e}")
            raise ValueError(f"Client information not valid")
        
        finally:
            conn.close()

