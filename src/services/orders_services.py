import sqlite3

from src.models.order import OrderStatus
from src.utils.logger import setup_logger

class OrdersServices:
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = setup_logger('orders_services')

    def create_order(self, order):
        """
        Usamos esta función para guardar la orden en la base de datos.

        :param order: Order
        :param user_id: int
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                INSERT INTO orders (order_side, order_type, quantity, remaining_quantity, price, ticker, client_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
                """
                cursor.execute(
                    query, (order.order_side, order.order_type, order.quantity, order.quantity,
                            order.price, order.ticker, order.client_id)
                )
                order_id = cursor.lastrowid
                conn.commit()
                self.logger.info(f'Order saved in DB: ID ({order_id})')
                return order_id
            
        except Exception as e:
            self.logger.error(f"Error creating order: {e}")
            raise e
    
    def get_pending_orders(self):
        """
        Función para leer todas las órdenes activas (status = PENDING)
        """
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM orders WHERE status = ? ORDER BY id ASC",
                (OrderStatus.PENDING.value,)
            )
            res = cursor.fetchall()
            
            return [dict(row) for row in res]
    
    def cancel_order(self, order):
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE orders SET status = ? WHERE id = ?",
                    (OrderStatus.CANCELLED, order.id)
                )
                conn.commit()

        except sqlite3.IntegrityError as e:
            self.logger.error(f"Error updating orders after not match: {e}")
            return None
        
        except Exception as e:
            self.logger.critical(f"Critical error updating orders without match: {e}")
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
                    tr.execute("""
                        UPDATE orders 
                        SET remaining_quantity = remaining_quantity - ?,
                            status = CASE WHEN (remaining_quantity - ?) <= 0 THEN 'FILLED' ELSE 'PARTIALLY_FILLED' END
                        WHERE id = ?
                    """, (match_data['quantity'], match_data['quantity'], oid))

        except Exception as e:
            raise e