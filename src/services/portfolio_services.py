from pydantic import ValidationError

from src.models.client import ClientSearch
from src.utils.logger import setup_logger

class PortfolioServices:
    """
    Esta clase incluye todos los métodos relacionados con la gestión de los portfolios
    de los usuarios. Esto es, añadir o retirar fondos, añadir o retirar títulos
    """
    def __init__(self, db_manager, client_service):
        self.db = db_manager
        self.client_services = client_service
        self.logger = setup_logger('portfolio_services')

    def _update_cash(self, client_data, cash_variation):
        """
        Usamos esta función para modificar la cantidad de fondos en la cuenta de
        un cliente concreto. Es protegida porque solo la queremos llamar desde las 
        funciones concretas de añadir o retirar cash

        :param client_data: ClientSearch
        :param cash_variation: Número positivo para añadir fondos, negativo para retirar
        """

        try:
            client_id = self.client_services.get_client_id(client_data)
            
            if client_id is None:
                self.logger.warning(f"Cannot update cash: Client not found ({client_data.client_name})")
                return False
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                initial_amount = self.get_client_cash(client_data)

                query = """
                INSERT INTO portfolios (client_id, asset_id, quantity)
                VALUES (?, ?, MAX(0, ?))
                ON CONFLICT (client_id, asset_id)
                DO UPDATE SET quantity = portfolios.quantity + ?;
                """
                cursor.execute(query, (client_id, 'CASH', cash_variation, cash_variation))
                affected_row = cursor.rowcount

                if affected_row > 0:
                    self.logger.info(f"Client: {client_data.nickname}. Portfolio updated. 'CASH': {initial_amount} -> {initial_amount + cash_variation}")
                    conn.commit()

        except Exception as e:
            self.logger.error(f"Error updating cash: {e}")
            return -1
        
    def add_cash(self, client_name = None, client_email = None, quantity = 0):
        """
        Añadimos la cantidad introducida al portfolio del cliente
        
        :param client_data: Objeto ClientSearch
        :param quantity: Cantidad a añadir
        """
        try:
            client = ClientSearch(client_name=client_name, email=client_email)
            self._update_cash(client, quantity)
        
        except ValidationError as e:
            self.logger.error(f"Validation error: {e.errors()}")
            raise Exception(e)

    def withdraw_cash(self, client_name = None, client_email = None, quantity = 0):
        """
        Retiramos la cantidad introducida al portfolio del cliente
        
        :param client_data: Objeto ClientSearch
        :param quantity: Cantidad a retirar
        """
        try:
            client = ClientSearch(client_name=client_name, email=client_email)
            
            current_cash = self.get_client_cash(client)

            if quantity > current_cash:
                self.logger.warning(f"Client {client.nickname} tried to withdraw more money than he has")
            else:
                # Convertimos en negativo para que reste
                self._update_cash(client, quantity * -1)
        
        except ValidationError as e:
            self.logger.error(f"Validation error: {e.errors()}")
            raise Exception(e)
    
    def get_client_cash(self, client_data):
        """
        Función para obtener el dinero que el cliente mantiene en su cuenta.
        :param client_data: ClientSearch
        """
        try:
            client_id = self.client_services.get_client_id(client_data)
            if client_id is None:
                return None
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT quantity FROM portfolios WHERE client_id = ? AND asset_id = 'CASH'",
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