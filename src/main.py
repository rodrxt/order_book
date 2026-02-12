from src.utils.database import DataBaseManager
from src.services.clients_services import add_client

def initialize():
    db = DataBaseManager()
    db.init_db()

def main():
    add_client('Example_name', 'example@gmail.com')
    
if __name__ == '__main__':
    main()