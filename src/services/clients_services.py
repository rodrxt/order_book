import sqlite3

from pydantic import ValidationError

from src.models.client import Client, ClientSearch
from src.utils.logger import setup_logger

class ClientServices:
    """
    Esta clase gestiona todas las acciones relacionadas con los clientes: creación,
    borrado, consulta de id, etc.
    """
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = setup_logger('clients_services')

    def add_client(self, client_name, client_email):
        """
        Esta función se usa para añadir un cliente a nuestra base de datos
        """
        try:
            new_client = Client(client_name=client_name, email=client_email)

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "INSERT INTO clients (client_name, email) VALUES (?, ?)",
                    (new_client.client_name, new_client.email)
                )
                # guardamos el id del usuario creado
                client_id = cursor.lastrowid
                
                conn.commit()
                self.logger.info(f"Client created: {new_client.client_name} (ID: {client_id})")
                
                return client_id
            
        except sqlite3.IntegrityError as e:
            self.logger.warning(f"Client already exists: {new_client.client_name}")
            return None

        except ValidationError as e:
            self.logger.error(f"Validation error adding client: {e}")
            raise e
        
        except Exception as e:
            self.logger.error(f"Database error adding client: {e}")
            raise Exception(f"Could not add client: {e}")

    def remove_client(self, client_name = None, client_email = None):
        """
        Esta función se usa para eliminar un cliente a nuestra base de datos
        utilizando o su email o su nombre de usuario
        """
        try:
            # Ejecutamos primero para evitar cómputo innecesario
            client = ClientSearch(client_name=client_name, email=client_email)

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM clients WHERE client_name = ? OR email = ?",
                    (client.client_name, client.email)
                )
                conn.commit()
                
                if cursor.rowcount == 0:
                    # No se ha borrado ningún usuario
                    self.logger.info(f"Delete skipped: Client not found ({client.client_name})")
                    return False
                
                elif cursor.rowcount == 1:
                    self.logger.info(f"Client deleted: {client.client_name}")
                    return True
                
                else:
                    # No se deberían borrar nunca más de 1 usuario a la vezm
                    # dado que la tabla no debería tener duplicados
                    self.logger.critical(f"More than one client has been removed with the same credentials")
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
            with self.db.get_connection() as conn:
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