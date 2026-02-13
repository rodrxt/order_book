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

        self._init_db()
    
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
        
        try:
            with self._get_connection() as conn: 
                with open(create_tables_sql, 'r') as f:
                    create_orders_query = f.read()
                conn.executescript(create_orders_query)
                conn.commit()

                self.logger.info("Tables initialized")
        
        except Exception as e:
            self.logger.critical(f"Error while initializing tables: {e}")
            raise e

    def add_new_client(self, client_data):
        """
        Usamos esta función para añadir un cliente a la db
        """

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO clients (client_name, email) VALUES (?, ?)",
                    (client_data.client_name, client_data.email)
                )
                # guardamos el id del usuario creado
                client_id = cursor.lastrowid
                
                conn.commit()
                self.logger.info(f"Client created: {client_data.client_name} (ID: {client_id})")
                
                return client_id
        
        except sqlite3.IntegrityError as e:
            self.logger.warning(f"Client already exists: {client_data.client_name}")
            return None
        
        except Exception as e:
            self.logger.error(f"Database error adding client: {e}")
            raise Exception(f"Could not add client: {e}")
    
    def delete_client(self, client_data):
        """
        Usamos esta función para borrar un cliente de la db
        """

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM clients WHERE client_name = ? OR email = ?",
                    (client_data.client_name, client_data.email)
                )
                conn.commit()
                
                if cursor.rowcount == 0:
                    # No se ha borrado ningún usuario
                    self.logger.info(f"Delete skipped: Client not found ({client_data.client_name})")
                    return False
                
                elif cursor.rowcount == 1:
                    self.logger.info(f"Client deleted: {client_data.client_name}")
                    return True
                
                else:
                    # No se deberían borrar nunca más de 1 usuario a la vezm
                    # dado que la tabla no debería tener duplicados
                    self.logger.error(f"More than one client has been removed with the same credentials")
                    return False
        
        except Exception as e:
            self.logger.error(f"Error deleting client: {e}")
            raise Exception(e)
    
    def get_client_id(self, client_data):
        """
        Usamos esta función para obtener el id de un usuario con su nombre o email
        :param client_data: ClientSearch
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM clients WHERE client_name = ? OR email = ?",
                    (client_data.client_name, client_data.email)
                )
                
                res = cursor.fetchone()
                if res:
                    return res[0]
                
                # No existe el usuario
                return None
            
        except Exception as e:
            self.logger.error(f"Error reading client ID: {e}")
            raise Exception(e)
        

    def get_client_cash(self, client_data):
        """
        Función para obtener el dinero que el cliente mantiene en su cuenta.
        :param client_data: ClientSearch
        """
        try:
            client_id = self.get_client_id(client_data)
            if client_id is None:
                return None
            
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT quantity FROM portfolios WHERE client_id = ?",
                    (client_id,)
                )
                res = cursor.fetchone()
                if res:
                    return res[0]
                
                # Si no existe la fila, pero sí el usuario, consideramos que tiene 0 
                return 0
        except Exception as e:
            self.logger.error(f"Error reading user cash information: {e}")
            raise Exception(e)

    def update_cash(self, client_data, cash_variation):
        """
        Usamos esta función para modificar la cantidad de fondos en la cuenta de
        un cliente concreto

        :param client_data: ClientSearch
        :param cash_variation: Número positivo para añadir fondos, negativo para retirar
        """

        try:
            client_id = self.get_client_id(client_data)
            
            if client_id is None:
                self.logger.warning(f"Cannot update cash: Client not found ({client_data.client_name})")
                return False
            
            with self._get_connection() as conn:
                cursor = conn.cursor()

                initial_amount = self.get_client_cash(client_data)

                query = """
                INSERT INTO portfolios (client_id, asset_id, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT (client_id, asset_id)
                DO UPDATE SET quantity = portfolios.quantity + excluded.quantity;
                """
                cursor.execute(query, (client_id, 'CASH', cash_variation))
                affected_row = cursor.rowcount

                if affected_row > 0:
                    self.logger.info(f"Client: {client_data.nickname}. Portfolio updated. 'CASH': {initial_amount} -> {initial_amount + cash_variation}")
                    conn.commit()

        except Exception as e:
            self.logger.error(f"Error updating cash: {e}")
            return -1


