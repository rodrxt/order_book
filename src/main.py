from src.utils.database import DataBaseManager
from src.services.clients_services import ClientServices
from src.services.portfolio_services import PortfolioServices
from src.models.client import ClientSearch

def main():
    db_manager = DataBaseManager()
    clients_services = ClientServices(db_manager=db_manager)
    portfolio_services = PortfolioServices(db_manager=db_manager, client_service=clients_services)
    
    # clients_services.add_client(client_name='Example_name', client_email='example@gmail.com')
    # clients_services.remove_client(client_name='Example_name')
    
    # client = ClientSearch(client_name='Example_name')
    # print(portfolio_services.get_client_cash(client))
    portfolio_services.withdraw_cash(client_name='Example_name', quantity=100)
    # 
    # ret = add_client(client_name='Example_name2', client_email='example2@gmail.com')
    # ret = add_cash(client_name='Example_name2', quantity=100)
    # ret = withdraw_cash(client_name = 'Example_name', quantity=10)
    # remove_client(client_name='Example_name')
 
    
if __name__ == '__main__':
    main()