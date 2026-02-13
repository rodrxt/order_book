from pydantic import ValidationError

from src.utils.database import DataBaseManager
from src.models.client import ClientSearch

db = DataBaseManager()

def add_cash(client_name = None, client_email = None, quantity = 0):
    """
    Añadimos la cantidad introducida al portfolio del cliente
    
    :param client_data: Objeto ClientSearch
    :param quantity: Cantidad a añadir
    """
    try:
        client = ClientSearch(client_name=client_name, email=client_email)
        db.update_cash(client, quantity)
    
    except ValidationError as e:
        db.logger.error(f"Validation error: {e.errors()}")
        raise Exception(e)

def withdraw_cash(client_name = None, client_email = None, quantity = 0):
    """
    Retiramos la cantidad introducida al portfolio del cliente
    
    :param client_data: Objeto ClientSearch
    :param quantity: Cantidad a retirar
    """
    try:
        client = ClientSearch(client_name=client_name, email=client_email)
        
        current_cash = db.get_client_cash(client)

        if quantity > current_cash:
            db.logger.warning(f"Client {client.nickname} tried to withdraw more money than he has")
        else:
            # Convertimos en negativo para que reste
            db.update_cash(client, quantity * -1)
    
    except ValidationError as e:
        db.logger.error(f"Validation error: {e.errors()}")
        raise Exception(e)