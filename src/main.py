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

def main():
    logger = setup_logger("main")
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
    print(f"""
    Commands:
    \t- CREATE USER user_name user_email
    \t- ADD ASSET ticker quantity user_name
    \t- ORDER order_side order_type ticker quantity user_name price
    \t- exit
    """)
    while True:
        try:
            raw_input = input("> ").strip()
            if not raw_input: continue
            if raw_input.lower() == 'exit': break

            parts = raw_input.split()
            cmd = parts[0].upper()

            if cmd == "CREATE" and parts[1].upper() == 'USER':
                user_name = parts[2]
                user_email = parts[3]
                clients_services.add_client(
                    client_name=user_name, 
                    client_email=user_email
                )

            elif cmd == "ADD" and parts[1].upper() == "ASSET":
                ticker = parts[2].upper()
                qty = int(parts[3])
                user_ref = parts[4]
                    
                try:
                    if ticker == "CASH":
                        res = portfolio_services.add_cash(client_name=user_ref, quantity=qty)
                    else:
                        client = ClientSearch(
                            client_name=user_ref
                        )
                        
                        res = portfolio_services.update_asset(client_data=client, asset_variation=qty, asset_id=ticker)
                    
                    if res is not None:
                        logger.info(f'Asset quantity updated: {user_ref} -> ({ticker}, {qty})')
                
                except Exception as e:
                    logger.error(f"Error updating asset quantity: {e}")

            elif cmd == "ORDER":
                side_str = parts[1].upper()
                type_str = parts[2].upper()
                ticker = parts[3].upper()
                qty = int(parts[4])
                user_name = parts[5]
                price = float(parts[6]) if len(parts) > 6 else None

                client_search = ClientSearch(
                    client_name=user_name
                )

                client_id = clients_services.get_client_id(client_search)

                side = OrderSide.BID if side_str == "BUY" or side_str == "BID" else OrderSide.ASK
                order_type = OrderType[type_str]

                new_order = Order(
                    client_id=client_id,
                    ticker=ticker,
                    quantity=qty,
                    remaining_quantity=qty,
                    price=price,
                    order_side=side,
                    order_type=order_type,
                    status=OrderStatus.PENDING
                )

                matches = trading_engine.place_order(new_order)

                if matches != False:
                    logger.info(f"Order {side_str} of {ticker} processed.")
                else:
                    logger.warning(f"Order not processed: {new_order}")
            
            else:
                logger.warning(f"Invalid command: {raw_input}")

        except IndexError:
            logger.error("Format error.")
        except ValidationError as e:
            logger.error(f"Incorrect order format: {e}")
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()