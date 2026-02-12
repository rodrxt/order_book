from pydantic import ValidationError

from src.models.client import Client
from src.utils.database import DataBaseManager

db = DataBaseManager()

def add_client(client_name, client_email):
    """
    Esta función se usa para añadir un cliente a nuestra base de datos
    """
    try:
        new_client = Client(client_name=client_name, email=client_email)
        id_client = db.add_new_client(new_client)
        print(f"Id: {id_client}")
        
    except ValidationError as e:
        db.logger.error(f"Validation error: {e.errors()}")

def remove_client():
    pass