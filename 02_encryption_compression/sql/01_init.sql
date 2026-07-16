CREATE TABLE IF NOT EXISTS secure_data (
    id SERIAL PRIMARY KEY,
    secret_key VARCHAR(100) NOT NULL,
    secret_value VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO secure_data (secret_key, secret_value) VALUES
('ApiKey', 'sk_test_51Nx...'),
('DbPassword', 'supersecretpassword'),
('EncryptionSalt', '0x7ffd98b7e28a');
