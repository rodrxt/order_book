import sys

from pydantic import ValidationError

from src.utils.database import DataBaseManager
from src.utils.logger import setup_logger
from src.services.clients_services import ClientServices
from src.services.portfolio_services import PortfolioServices
from src.services.orders_services import OrdersServices
from src.engine.processor import TradingEngine

from src.models.order import Order, OrderSide, OrderType, OrderStatus
from src.models.client import ClientSearch

def create_users(clients_services, portfolio_services):
    client_1_name = "Example1"
    client_1_email = "example@gmail.com"
    client_2_name = "Example2"
    client_2_email = "example2@gmail.com"

    client_id_1 = clients_services.add_client(
        client_name=client_1_name, 
        client_email=client_1_email
    )
    
    portfolio_services.add_cash(
        client_email=client_1_email, 
        quantity=10000
    )

    client = ClientSearch(
        client_name = client_1_name
    )

    portfolio_services.update_asset(
        client, 100, 'AAPL'
    )

    client_id_2 = clients_services.add_client(
        client_name=client_2_name, 
        client_email=client_2_email
    )
    
    portfolio_services.add_cash(
        client_email=client_2_email, 
        quantity=10000
    )

    return client_id_1, client_id_2

def place_bid_order(logger, client_2_id, trading_engine):
    try:
        logger.info("Placing order...")
        new_order = Order(
            client_id=client_2_id,
            ticker="AAPL",
            quantity=10,
            remaining_quantity=10,
            price=150,
            order_side=OrderSide.BID,
            order_type=OrderType.LIMIT,
            status=OrderStatus.PENDING
        )

        resultado = trading_engine.place_order(new_order)
        
        if resultado:
            logger.info("Order processed correctly.")
        else:
            logger.warning("Order rejected")

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise e
    
    except Exception as e:
        logger.error(f"Critical error in the system: {e}")
        raise e
    
def place_ask_order(logger, client_1_id, trading_engine):
    try:
        logger.info("Placing order...")
        new_order = Order(
            client_id=client_1_id,
            ticker="AAPL",
            quantity=5,
            remaining_quantity=5,
            order_side=OrderSide.ASK,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING
        )

        resultado = trading_engine.place_order(new_order)
        
        if resultado:
            logger.info("Order processed correctly.")
        else:
            logger.warning("Order rejected")
            
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise e
    
    except Exception as e:
        logger.error(f"Critical error in the system: {e}")
        raise e

def main():
    logger = setup_logger("MAIN")
    db_manager = DataBaseManager()

    clients_services = ClientServices(db_manager=db_manager)
    
    portfolio_services = PortfolioServices(
        db_manager=db_manager, 
        client_service=clients_services
    )
    
    orders_services = OrdersServices(db_manager=db_manager)
    
    trading_engine = TradingEngine(
        db_manager=db_manager,
        orders_service=orders_services,
        clients_service=clients_services,
        portfolio_services=portfolio_services
    )

    try:
        logger.info("Preparing scenario...")
        
        client_1_id, client_2_id = create_users(clients_services, portfolio_services)

        place_bid_order(logger, client_2_id, trading_engine)

        place_ask_order(logger, client_1_id, trading_engine)
    
    except Exception as e:
        logger.error(f"Critical error in the system: {e}")
        raise e

if __name__ == "__main__":
    main()