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
        self.logger = setup_logger("database")

        if not os.path.exists(DATA_DIR):
            self.logger.debug("Data folder does not exist yet. Starting creation.")
        
        os.makedirs(DATA_DIR, exist_ok=True)

        if self._init_db() == -1:
            return -1
    
    def _get_connection(self):
        """
        Usamos un método privado para mayor seguridad. Solo lo podemos desde funciones internas
        """
        conn = sqlite3.connect(DB_DIR)
        # Usamos esto para habilitar las foreign keys en las tablas
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        """
        Utilizo esta función para inicializar las tablas que vamos a usar
        """
        create_tables_sql = SQL_DIR / "create_tables.sql"

        with self._get_connection() as conn: 
            try:
                with open(create_tables_sql, 'r') as f:
                    create_orders_query = f.read()
                conn.executescript(create_orders_query)
                conn.commit()

                self.logger.info("Tables initialized")
                return conn
            
            except Exception as e:
                self.logger.error(f"Error while initializing tables: {e}")
                return -1

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
            
            conn.commit()
            self.logger.info(f"Client {client_id}: {client_data.client_name} created successfully")
            
            return client_id
        
        except sqlite3.IntegrityError as e:
            # Si algo falla, volvemos al estado previo
            conn.rollback()
            self.logger.error(f"Integrity error while creating new client: {e}")
            return -1
        
        finally:
            conn.close()
    
    def delete_client(self, client_data):
        """
        Usamos esta función para borrar un cliente de la db
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM clients WHERE client_name = ? OR email = ?",
                (client_data.client_name, client_data.email)
            )
            n_clients_deleted = cursor.rowcount
            print(n_clients_deleted)
            conn.commit()
            if n_clients_deleted == 0:
                # No se ha borrado ningún usuario
                self.logger.debug(f"No match with databse. Couldn't remove client")
            
            elif n_clients_deleted == 1:
                self.logger.info(f"User {client_data.identifier_string} deleted.")
            
            else:
                self.logger.error(f"More than one user has been removed with the same credentials")
                return -1
            
            return 1
        
        except sqlite3.IntegrityError as e:
            # Si algo falla, volvemos al estado previo
            conn.rollback()
            self.logger.error(f"Integrity error while deleting new client: {e}")
            return -1
        
        finally:
            conn.close()

