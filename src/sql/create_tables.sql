CREATE TABLE IF NOT EXISTS clients(
    id INTEGER PRIMARY KEY,
    client_name TEXT UNIQUE,
    email TEXT UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolios(
    id INTEGER PRIMARY KEY,
    client_id INTEGER,
    asset_id TEXT,
    quantity DECIMAL NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    UNIQUE (client_id, asset_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    order_side TEXT CHECK (order_side IN ('ASK', 'BID')),
    order_type TEXT CHECK (order_type IN ('MARKET', 'LIMIT', 'BEST')),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity > 0),
    remaining_quantity INTEGER NOT NULL DEFAULT 0 CHECK (remaining_quantity >= 0),
    price DECIMAL CHECK (price > 0.0), 
    ticker TEXT NOT NULL,
    client_id INTEGER,
    status TEXT CHECK (status IN ('PENDING', 'FILLED', 'PARTIALLY_FILLED', 'CANCELLED')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,  
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT
);

CREATE TRIGGER IF NOT EXISTS clean_empty_cash
AFTER UPDATE OF quantity ON portfolios
FOR EACH ROW
WHEN NEW.asset_id = 'CASH' AND NEW.quantity = 0
BEGIN
    DELETE FROM portfolios WHERE id = NEW.id;
END;

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);