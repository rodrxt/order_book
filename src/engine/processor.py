from src.utils.logger import setup_logger
from src.models.order import OrderSide, OrderType, OrderStatus
from src.engine.order_book import OrderBook

class TradingEngine:
    def __init__(self, db_manager, orders_service, clients_service, portfolio_services):
        self.db = db_manager
        self.orders_services = orders_service
        self.clients_services = clients_service
        self.portfolio_services = portfolio_services
        self.order_book = OrderBook()
        self.logger = setup_logger('engine_processor')

        self._load_order_book()

    def _load_order_book(self):
        """
        Con esta función, cargamos en memoria la información de la DB
        """
        self.logger.info("Loading DB information into memory...")
        pending_orders = self.orders_services.get_pending_orders()
        
        for order_data in pending_orders:
            self.order_book.save_order(order_data)
 
        self.logger.info(f"Information loaded. {len(pending_orders)} orders loaded.")

    def place_order(self, order):
        """
        Aquí se procesa la validez de la orden y se llama a la función que inserta la 
        orden en la base de datos si todo es correcto
        """
        # En caso de ser una operación del Ask, es necesario comprobar que 
        # el cliente tiene los activos que quiere vender con la operación

        if order.order_side == OrderSide.ASK:
            asset_quantity = self.portfolio_services.get_client_asset_quantity(order.client_id, order.ticker)
            
            if asset_quantity < order.quantity:
                # Esto quiere decir que está intentando vender más de lo que tiene
                self.logger.warning(f"User is trying to sell more than possible amount. Order: ({order.ticker}, {order.quantity}), Portfolio: ({order.ticker}, {asset_quantity})")
                return False
        
        if order.order_side == OrderSide.BID and order.order_type == OrderType.LIMIT:
            # Si no es una orden límite, no tendrá precio determinado y la validación
            # debe hacerse de otra manera

            cost = order.price * order.quantity
            client_cash = self.portfolio_services.get_client_asset_quantity(order.client_id, 'CASH')
            # Si es de compra, debe tener fondos suficientes
            if cost > client_cash:
                self.logger.warning(f"Client has not enough cash to complete the order: ID ({order.client_id}), Cash: {client_cash}, Order cost: {cost}")
                return False
        
        try:
            order_id = self.orders_services.create_order(order)

            order.id = order_id
        
        except Exception as e:
            self.logger.error(f"DB Error creating order: {e}")
            return False
        try:
            if order.order_side == OrderSide.BID and (order.order_type == OrderType.MARKET or order.order_type == OrderType.BEST):
                # En este caso hay que pasarle el saldo actual del cliente al motor de match
                client_cash = self.portfolio_services.get_client_asset_quantity(order.client_id, 'CASH')

                match_result = self.order_book.match(order, client_cash)

            else:
                match_result = self.order_book.match(order)
            
            if match_result and len(match_result) > 0:
                self.process_match(match_result, order)
            else:
                # Gestionamos si no hubo match
                self.process_not_match(order)

        except Exception as e:
            # Si hay algún fallo antes de procesarla por completo, cancelamos la orden
            self.orders_services.cancel_order(order)

        return match_result
    
    def process_not_match(self, order):
        # Si la orden es de mercado o por lo mejor, si no hubo match cambiamos status a CANCELLED, 
        # pero no hacemos nada. Si es una orden límite, la dejamos en PENDING
        if order.order_type in (OrderType.MARKET, OrderType.BEST):
            self.orders_services.cancel_order(order)
            self.logger.info(f"Order {order.id} was cancelled: No match found")
    
    def process_match(self, matches, order):
        try:
            self.logger.info(f"Processing {len(matches)} matches...")
            
            for match in matches:
                
                ticker = match['ticker']
                qty = match['quantity']
                price = match['price']

                total_cost = qty * price
                
                self.logger.info(f"MATCH: {ticker} | {qty} u. @ {price}$ | Buyer: {match['bid_order_client_id']} <-> Seller: {match['ask_order_client_id']}")

                self.portfolio_services.execute_trade(
                    buyer_id=match['bid_order_client_id'],
                    seller_id=match['ask_order_client_id'],
                    ticker=ticker,
                    quantity=qty,
                    total_price=total_cost
                )

                # Ahora actualizamos la base de datos
                self.portfolio_services.register_trade_execution(match)
            
            # Al final, comprobamos que si la orden es de mercado o por lo mejor, no quede
            # abierta
            if order.order_type in (OrderType.MARKET, OrderType.BEST):
                # La borramos de memoria
                self.order_book.remove_order(order=order)

                # La etiquetamos como PARTIALLY_FILLED
                self.orders_services.change_order_status(order=order, new_status = OrderStatus.PARTIALLY_FILLED)

        except Exception as e:
            self.logger.critical(f"Error processing match: {e}")
            raise e