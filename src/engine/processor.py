from src.utils.logger import setup_logger
from src.models.order import OrderSide
from src.engine.order_book import OrderBook, OrderType

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
        
        if order.order_side == OrderSide.BID:
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
        
        match_result = self.order_book.match(order)
        
        if match_result:
            self.process_match(match_result, order)
        else:
            # Gestionamos si no hubo match
            self.process_not_match(order)

        return 1
    
    def process_not_match(self, order):
        # Si la orden es de mercado, si no hubo match cambiamos status a CANCELLED, 
        # pero no hacemos nada. Si es una orden límite, la dejamos en PENDING
        if order.order_type == OrderType.MARKET:
            self.orders_services.cancel_order(order)

    
    def process_match(self, matches, order):
        try:
            self.logger.info(f"Processing {len(matches)} matches...")

            for match in matches:

                if order.order_side == OrderSide.ASK:
                    ask_order = order
                else:
                    ask_order = self.order_book.get_order_by_id(match['ask_order_id'], OrderSide.ASK)

                if order.order_side == OrderSide.BID:
                    bid_order = order
                else:
                    bid_order = self.order_book.get_order_by_id(match['bid_order_id'], OrderSide.BID)

                ticker = match['ticker']
                qty = match['quantity']
                price = match['price']

                total_cost = qty * price

                self.logger.info(f"MATCH: {ticker} | {qty} u. @ {price}$ | Buyer: {bid_order.client_id} <-> Seller: {ask_order.client_id}")

                self.portfolio_services.execute_trade(
                    buyer_id=bid_order.client_id,
                    seller_id=ask_order.client_id,
                    ticker=ticker,
                    quantity=qty,
                    total_price=total_cost
                )

                # Ahora actualizamos la base de datos
                self.orders_services.update_after_match(match['bid_order_id'], qty)
                self.orders_services.update_after_match(match['ask_order_id'], qty)

        except Exception as e:
            self.logger.critical(f"Error processing match: {e}")
            raise e