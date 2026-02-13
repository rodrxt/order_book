from src.utils.database import DataBaseManager
from src.services.clients_services import add_client, remove_client


def main():
    ret = add_client(client_name='Example_name', client_email='example@gmail.com')

    ret = remove_client(client_email="example@gmail.com")
    if ret == -1:
        return -1
    
if __name__ == '__main__':
    main()