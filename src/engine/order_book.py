from pydantic import ValidationError

from src.models.order import OrderSide, Order, OrderType

class OrderBook:
    def __init__(self):
        self.bids = []
        self.asks = []

    def get_order_by_id(self, order_id, order_side):
        if order_side == OrderSide.ASK:
            for elem in self.asks:
                if elem.id == order_id:
                    return elem
        elif order_side == OrderSide.BID:
            for elem in self.bids:
                if elem.id == order_id:
                    return elem
        return None
    
    def save_order(self, order_data):
        """
        Usamos esta función para rellenar este objeto con datos de la base de datos
        
        :param order_data: dict
        """
        try:
            order_object = order_data
            if not isinstance(order_data, Order):
                order_object = Order(
                    id = order_data['id'],
                    order_side=order_data['order_side'],
                    order_type=order_data['order_type'],
                    quantity=order_data['quantity'],
                    remaining_quantity=order_data['quantity'],
                    price=order_data['price'],
                    ticker=order_data['ticker'],
                    client_id=order_data['client_id'],
                    status=order_data['status']
                )

        except ValidationError as e:
            self.logger.error(f"Could not add order to the Order Book. Incorrect data: {e}")
            raise e
        
        if order_object.order_side == OrderSide.ASK:
            self.insert_ordered(order_object)
        else:
            self.insert_ordered(order_object)
    
    def remove_order(self, order):
        target_list = self.asks if order.order_side == OrderSide.ASK else self.bids
    
        for i, existing_order in enumerate(target_list):
            if existing_order.id == order.id:

                target_list.pop(i)
                return True
                
        return False

    def insert_ordered(self, order_object):
        inserted = False
        
        if order_object.order_side == OrderSide.ASK:
            # Orden ascendente para Ask
            # Buscamos el primer hueco donde mi precio sea menor que el actual
            for i, existing_order in enumerate(self.asks):

                if order_object.price < existing_order.price:
                    self.asks.insert(i, order_object)
                    inserted = True
                    break
            
            # Si no se encontró hueco (es el más caro de todos), va al final
            if not inserted:
                self.asks.append(order_object)

        else:
            # Orden descendente para Bid
            for i, existing_order in enumerate(self.bids):
                if order_object.price > existing_order.price:
                    self.bids.insert(i, order_object)
                    inserted = True
                    break

            if not inserted:
                self.bids.append(order_object)

    def match(self, order, buyer_balance = None):
        matches = []

        if order.order_side == OrderSide.ASK:
            matches = self._match_ask(order)
        else:
            matches = self._match_bid(order, buyer_balance)
            
        return matches

    def _match_bid(self, bid_order, buyer_balance = None):
        """
        Aquí procesamos las órdenes de compra. Se debe tener en cuenta el tipo de órden
        
        :param bid_order: Order
        """
        if bid_order.order_type == OrderType.MARKET:
            return self._match_bid_market(bid_order=bid_order, buyer_balance=buyer_balance)
        elif bid_order.order_type == OrderType.BEST:
            return self._match_bid_best(bid_order=bid_order, buyer_balance=buyer_balance)
        elif bid_order.order_type == OrderType.LIMIT:
            return self._match_bid_limit(bid_order=bid_order)

    def _match_bid_limit(self, bid_order):
        trades = []

        # Se insertan ordenados ya
        while bid_order.remaining_quantity > 0 and len(self.asks) > 0 and bid_order.price >= self.asks[0].price:
            best_ask = self.asks[0]

            traded_quantity = min(best_ask.remaining_quantity, bid_order.remaining_quantity)
            
            trades.append(
                {
                    'bid_order_id': bid_order.id,
                    'ask_order_id': best_ask.id,
                    'ticker': best_ask.ticker,
                    'price': best_ask.price,
                    'quantity': traded_quantity
                }
            )

            best_ask.remaining_quantity -= traded_quantity
            bid_order.remaining_quantity -= traded_quantity

            if best_ask.remaining_quantity == 0:
                self.asks.pop(0)
        
        if bid_order.remaining_quantity > 0:
            self.save_order(bid_order)
        
        return trades

    def _match_bid_market(self, bid_order, buyer_balance):
        """
        Esta función se encarga de encontrar los match para ordenes BID de mercado. En caso 
        de que el cliente no pueda pagar por la cantidad que pidió, se procesa la compra
        hasta su límite de saldo

        :param bid_order: Order
        :param buyer_balance: float
        """

        trades = []

        while bid_order.remaining_quantity > 0 and len(self.asks) > 0:
            best_ask = self.asks[0]
            intended_quantity = min(best_ask.remaining_quantity, bid_order.remaining_quantity)

            cost = intended_quantity * best_ask.price

            if buyer_balance < cost:
                # El cliente no tiene suficiente saldo
                actual_quantity = int(buyer_balance // best_ask.price)

                if actual_quantity == 0:
                    break
            else:
                actual_quantity = intended_quantity

            actual_cost = actual_quantity * best_ask.price

            trades.append({
                'bid_order_id': bid_order.id,
                'bid_order_client_id': bid_order.client_id,
                'ask_order_id': best_ask.id,
                'ask_order_client_id': best_ask.client_id,
                'ticker': best_ask.ticker,
                'price': best_ask.price,
                'quantity': actual_quantity
            })

            best_ask.remaining_quantity -= actual_quantity
            bid_order.remaining_quantity -= actual_quantity
            buyer_balance -= actual_cost

            if best_ask.remaining_quantity == 0:
                self.asks.pop(0)

            if actual_quantity < intended_quantity:
                # Esto es que el cliente se quedó sin dinero
                break
        
        return trades

    def _match_bid_best(self, bid_order, buyer_balance):

        if len(self.asks) == 0:
            # Si no hay ordenes en el ask, anulamos la operación
            return []
        
        bid_order.price = self.asks[0].price

        # Ahora determinamos si el usuario puede realizar la compra
        if bid_order.quantity * bid_order.price > buyer_balance:
            # No hay saldo suficiente
            return []

        return self._match_bid_limit(bid_order)

    def _match_ask(self, ask_order):
        """
        Aquí procesamos las órdenes de venta. Se debe tener en cuenta el tipo de órden
        
        :param ask_order: Order
        """
        if ask_order.order_type == OrderType.MARKET:
            return self._match_ask_market(ask_order=ask_order)
        elif ask_order.order_type == OrderType.BEST:
            return self._match_ask_best(ask_order=ask_order)
        elif ask_order.order_type == OrderType.LIMIT:
            return self._match_ask_limit(ask_order=ask_order)
    
    def _match_ask_market(self, ask_order):
        """
        Intenta vender al mejor precio que haya en el bid
        
        :param ask_order: Order
        """
        trades = []
        # Mientras aún queden órdenes de compra y aún no se haya vendido todo lo que
        # se quiere vender, seguimos buscando
        while ask_order.remaining_quantity > 0 and len(self.bids) > 0:
            best_order = self.bids[0]

            traded_quantity = min(best_order.remaining_quantity, ask_order.remaining_quantity)
            
            trades.append(
                {
                    'bid_order_id': best_order.id,
                    'bid_order_client_id': best_order.client_id,
                    'ask_order_id': ask_order.id,
                    'ask_order_client_id': ask_order.client_id,
                    'ticker': best_order.ticker,
                    'price': best_order.price,
                    'quantity': traded_quantity
                }
            )

            ask_order.remaining_quantity -= traded_quantity
            best_order.remaining_quantity -= traded_quantity

            if best_order.remaining_quantity == 0:
                self.bids.pop(0)

        return trades

    def _match_ask_limit(self, ask_order):
        trades = []
        
        while ask_order.remaining_quantity > 0 and len(self.bids) > 0 and ask_order.price <= self.bids[0].price:
            best_bid = self.bids[0]

            traded_quantity = min(best_bid.remaining_quantity, ask_order.remaining_quantity)
            
            trades.append(
                {
                    'bid_order_id': best_bid.id,
                    'ask_order_id': ask_order.id,
                    'ticker': best_bid.ticker,
                    'price': best_bid.price,
                    'quantity': traded_quantity
                }
            )

            ask_order.remaining_quantity -= traded_quantity
            best_bid.remaining_quantity -= traded_quantity

            if best_bid.remaining_quantity == 0:
                self.bids.pop(0)
        
        if ask_order.remaining_quantity > 0:
            self.save_order(ask_order)
        
        return trades

    def _match_ask_best(self, ask_order):
        trades = []

        if len(self.bids) == 0:
            # Esto es que no hay ninguna orden y se queda todo en el ask
            self.save_order(ask_order) 
            return trades

        ask_order.price = self.bids[0].price

        # Se comporta igual que una orden limite para ese precio
        return self._match_ask_limit(ask_order)      