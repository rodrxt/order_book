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

    def update_after_match(self, order_id, matched_quantity):
        """
        Función para actualizar el estado de una órden cuando hay un match
        """
        try:
            with self.db.get_connection() as conn:
                # Para poder acceder como diccionario
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT remaining_quantity FROM orders WHERE id = ?", (order_id,))
                current_qty = cursor.fetchone()['remaining_quantity']
                
                new_qty = current_qty - matched_quantity
                
                new_status = 'FILLED' if new_qty <= 0 else 'PARTIALLY_FILLED'
                
                cursor.execute("""
                    UPDATE orders 
                    SET remaining_quantity = ?, status = ? 
                    WHERE id = ?
                """, (new_qty, new_status, order_id))
                
                conn.commit()

        except sqlite3.IntegrityError as e:
            self.logger.error(f"Error updating orders after match: {e}")
            return None
        
        except Exception as e:
            self.logger.critical(f"Critical error updating orders with match: {e}")
            raise e