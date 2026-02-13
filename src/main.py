from src.utils.database import DataBaseManager
from src.services.clients_services import add_client, remove_client
from src.services.portfolio_services import add_cash, withdraw_cash


def main():
    # ret = add_client(client_name='Example_name', client_email='example@gmail.com')
    # ret = add_cash(client_name='Example_name', quantity=100)
    # ret = withdraw_cash(client_name = 'Example_name', quantity=10)
    remove_client(client_name='Example_name')
 
    
if __name__ == '__main__':
    main()