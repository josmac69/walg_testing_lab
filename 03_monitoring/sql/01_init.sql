CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    item_name VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO inventory (item_name, quantity) VALUES
('Standard Widget', 50),
('Premium Gadget', 100),
('Super Sprocket', 25);
