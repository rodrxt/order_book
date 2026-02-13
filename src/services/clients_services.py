from pydantic import ValidationError

from src.models.client import Client, ClientDelete
from src.utils.database import DataBaseManager

db = DataBaseManager()

def add_client(client_name, client_email):
    """
    Esta función se usa para añadir un cliente a nuestra base de datos
    """
    try:
        new_client = Client(client_name=client_name, email=client_email)
        id_client = db.add_new_client(new_client)

    except ValidationError as e:
        db.logger.error(f"Validation error: {e.errors()}")
        return -1

def remove_client(client_name = None, client_email = None):
    """
    Esta función se usa para eliminar un cliente a nuestra base de datos
    utilizando o su email o su nombre de usuario
    """
    try:
        new_client = ClientDelete(client_name=client_name, email=client_email)
        id_client = db.delete_client(new_client)

    except ValidationError as e:
        db.logger.error(f"Validation error while removing client: Nor client name neither client email provided")
        return -1