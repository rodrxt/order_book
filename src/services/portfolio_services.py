from pydantic import ValidationError

from src.models.client import ClientSearch
from src.models.order import OrderType, OrderStatus
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

    def update_asset(self, client_data, asset_variation, asset_id):
        """
        Usamos esta función para modificar la cantidad de un activo en la cuenta de
        un cliente concreto.

        :param client_data: ClientSearch
        :param asset_variation: Número positivo para añadir unidades, negativo para retirar
        """

        try:
            client_id = self.client_services.get_client_id(client_data)
            
            if client_id is None:
                self.logger.warning(f"Cannot update {asset_id}: Client not found ({client_data.client_name})")
                return False
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                initial_amount = self.get_client_asset_quantity(client_data, asset_id)

                query = """
                INSERT INTO portfolios (client_id, asset_id, quantity)
                VALUES (?, ?, MAX(0, ?))
                ON CONFLICT (client_id, asset_id)
                DO UPDATE SET quantity = portfolios.quantity + ?;
                """
                cursor.execute(query, (client_id, asset_id, asset_variation, asset_variation))
                affected_row = cursor.rowcount

                if affected_row > 0:
                    self.logger.info(f"Client: {client_data.nickname}. Portfolio updated. {asset_id}: {initial_amount} -> {initial_amount + asset_variation}")
                    conn.commit()

        except Exception as e:
            self.logger.error(f"Error updating {asset_id}: {e}")
            return -1
        
    def add_cash(self, client_name = None, client_email = None, quantity = 0):
        """
        Añadimos la cantidad introducida al portfolio del cliente
        
        :param client_data: Objeto ClientSearch
        :param quantity: Cantidad a añadir
        """
        try:
            client = ClientSearch(client_name=client_name, email=client_email)
            
            self.update_asset(client, quantity, 'CASH')
        
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
            
            current_cash = self.get_client_asset_quantity(client, 'CASH')

            if quantity > current_cash:
                self.logger.warning(f"Client {client.nickname} tried to withdraw more money than he has")
            else:
                # Convertimos en negativo para que reste
                self.update_asset(client, quantity * -1, 'CASH')
        
        except ValidationError as e:
            self.logger.error(f"Validation error: {e.errors()}")
            raise Exception(e)
    
    def _resolve_client_id(self, client_identifier):
        """
        Método auxiliar que detecta si le pasamos un ID directo (int) o un objeto cliente (ClientSearch)
        """
        # si ya es un ID
        if isinstance(client_identifier, int):
            return client_identifier
            
        return self.client_services.get_client_id(client_identifier)
    
    def get_client_asset_quantity(self, client_data, asset_id):
        """
        Usamos esta función para obtener la cantidad que un usuario concreto tiene de 
        un activo concreto
        
        :param client_data: ClientSearch
        :param asset_id: str
        """

        try:
            client_id = self._resolve_client_id(client_data)
            if client_id is None:
                return None
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT quantity FROM portfolios WHERE client_id = ? AND asset_id = ?",
                    (client_id, asset_id)
                )
                res = cursor.fetchone()
                if res:
                    return res[0]
                
                # Si no existe la fila, pero sí el usuario, consideramos que tiene 0 
                return 0
            
        except Exception as e:
            self.logger.error(f"Error reading user asset information: {e}")
            raise Exception(e)
        
    def execute_trade(self, buyer_id, seller_id, ticker, quantity, total_price):
        """
        Esta función realiza el intercambio de activos de forma atómica.
        
        :param buyer_id: int
        :param seller_id: int
        :param ticker: str
        :param quantity: int
        :param total_price: int
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Comprador
                # Paga dinero (CASH disminuye)
                cursor.execute("""
                    INSERT INTO portfolios (client_id, asset_id, quantity) VALUES (?, 'CASH', ?)
                    ON CONFLICT(client_id, asset_id) DO UPDATE SET quantity = quantity - ?
                """, (buyer_id, total_price, total_price))
                
                # Recibe acciones (ticker aumenta)
                # Usamos UPSERT por si no tenía esa acción antes
                cursor.execute("""
                    INSERT INTO portfolios (client_id, asset_id, quantity) VALUES (?, ?, ?)
                    ON CONFLICT(client_id, asset_id) DO UPDATE SET quantity = quantity + ?
                """, (buyer_id, ticker, quantity, quantity))

                # Vendedor
                # Recibe dinero (CASH aumenta)
                cursor.execute("""
                    INSERT INTO portfolios (client_id, asset_id, quantity) VALUES (?, 'CASH', ?)
                    ON CONFLICT(client_id, asset_id) DO UPDATE SET quantity = quantity + ?
                """, (seller_id, total_price, total_price))
                
                # Entrega acciones (ticker disminuye)
                cursor.execute("""
                    UPDATE portfolios SET quantity = quantity - ? 
                    WHERE client_id = ? AND asset_id = ?
                """, (quantity, seller_id, ticker))

                conn.commit()
                self.logger.info(f"Trade executed: {buyer_id} bought {quantity} {ticker} from {seller_id}")
                
        except Exception as e:
            self.logger.error(f"Error executing trade assets: {e}")
            raise e
    
    def register_trade_execution(self, match_data):
        """
        Función para insertar en trades y actualizar orders de forma atómica.
        """
        try:
            with self.db.transaction() as tr: 
                tr.execute("""
                    INSERT INTO trades (bid_order_id, ask_order_id, ticker, quantity, price)
                    VALUES (?, ?, ?, ?, ?)
                """, (match_data['bid_order_id'], match_data['ask_order_id'], 
                    match_data['ticker'], match_data['quantity'], match_data['price']))

                for oid in [match_data['bid_order_id'], match_data['ask_order_id']]:
                    tr.execute(f"""
                        UPDATE orders 
                        SET remaining_quantity = remaining_quantity - ?,
                            status = CASE WHEN (remaining_quantity - ?) <= 0 THEN '{OrderStatus.FILLED.value}' ELSE status END
                        WHERE id = ?
                    """, (match_data['quantity'], match_data['quantity'], oid))

        except Exception as e:
            raise e
