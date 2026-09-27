-- =================================================================
-- TARGET DATABASE: E-COMMERCE SAMPLE DATASET & READ-ONLY ROLE
-- =================================================================

-- Drop existing tables if re-seeding
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- 1. Customers Table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(50) DEFAULT 'India',
    signup_date DATE NOT NULL DEFAULT CURRENT_DATE
);

-- 2. Products Table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(80) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    cost DECIMAL(10, 2) NOT NULL,
    stock_quantity INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. Orders Table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id) ON DELETE CASCADE,
    order_date DATE NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'completed', -- 'completed', 'pending', 'cancelled', 'refunded'
    shipping_city VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. Order Items Table
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id) ON DELETE RESTRICT,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL
);

-- 5. Payments Table
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(id) ON DELETE CASCADE,
    payment_method VARCHAR(50) NOT NULL, -- 'Credit Card', 'UPI', 'Net Banking', 'Cash on Delivery'
    payment_status VARCHAR(30) NOT NULL DEFAULT 'captured', -- 'captured', 'failed', 'refunded'
    amount DECIMAL(12, 2) NOT NULL,
    payment_date TIMESTAMP DEFAULT NOW()
);

-- =================================================================
-- SEED DATA
-- =================================================================

-- Customers
INSERT INTO customers (id, name, email, city, state, country, signup_date) VALUES
(1, 'Aarav Sharma', 'aarav.sharma@example.com', 'Mumbai', 'Maharashtra', 'India', '2023-01-10'),
(2, 'Priya Patel', 'priya.patel@example.com', 'Mumbai', 'Maharashtra', 'India', '2023-02-14'),
(3, 'Rohan Verma', 'rohan.verma@example.com', 'Delhi', 'Delhi', 'India', '2023-02-20'),
(4, 'Ananya Iyer', 'ananya.iyer@example.com', 'Bangalore', 'Karnataka', 'India', '2023-03-05'),
(5, 'Vikram Singh', 'vikram.singh@example.com', 'Jaipur', 'Rajasthan', 'India', '2023-03-18'),
(6, 'Sneha Kulkarni', 'sneha.k@example.com', 'Pune', 'Maharashtra', 'India', '2023-04-02'),
(7, 'Aditya Nair', 'aditya.nair@example.com', 'Kochi', 'Kerala', 'India', '2023-04-15'),
(8, 'Neha Gupta', 'neha.gupta@example.com', 'Mumbai', 'Maharashtra', 'India', '2023-05-12'),
(9, 'Rahul Roy', 'rahul.roy@example.com', 'Kolkata', 'West Bengal', 'India', '2023-06-01'),
(10, 'Divya Menon', 'divya.menon@example.com', 'Bangalore', 'Karnataka', 'India', '2023-06-25'),
(11, 'Karan Malhotra', 'karan.m@example.com', 'Delhi', 'Delhi', 'India', '2023-07-04'),
(12, 'Pooja Reddy', 'pooja.reddy@example.com', 'Hyderabad', 'Telangana', 'India', '2023-07-19'),
(13, 'Manish Chawla', 'manish.c@example.com', 'Mumbai', 'Maharashtra', 'India', '2023-08-01'),
(14, 'Tanvi Deshmukh', 'tanvi.d@example.com', 'Pune', 'Maharashtra', 'India', '2023-09-10'),
(15, 'Siddharth Joshi', 'siddharth.j@example.com', 'Ahmedabad', 'Gujarat', 'India', '2023-10-05');

-- Products
INSERT INTO products (id, name, category, price, cost, stock_quantity) VALUES
(1, 'Ultra HD 4K Smart TV 55"', 'Electronics', 44999.00, 32000.00, 45),
(2, 'Noise-Cancelling Wireless Headphones', 'Electronics', 7999.00, 4800.00, 120),
(3, 'Mechanical Gaming Keyboard RGB', 'Electronics', 4599.00, 2700.00, 80),
(4, 'Ergonomic Mesh Office Chair', 'Home & Furniture', 11499.00, 7200.00, 35),
(5, 'Solid Wood Study Desk', 'Home & Furniture', 8999.00, 5400.00, 25),
(6, 'Men Cotton Slim Fit Formal Shirt', 'Apparel', 1499.00, 650.00, 200),
(7, 'Women Handcrafted Silk Kurta', 'Apparel', 2499.00, 1100.00, 150),
(8, 'Stainless Steel Chef Knife Set', 'Kitchen & Dining', 2199.00, 1050.00, 90),
(9, 'Automatic Espresso Coffee Machine', 'Kitchen & Dining', 18999.00, 12500.00, 30),
(10, 'Fitness Smartwatch with Heart Rate Monitor', 'Fitness & Wearables', 3999.00, 2200.00, 110),
(11, 'Adjustable Cast Iron Dumbbell Set 20kg', 'Fitness & Wearables', 4999.00, 3100.00, 40),
(12, 'Python Data Analysis & ML Handbook', 'Books', 899.00, 450.00, 300);

-- Orders (Spanning 2023-2024 with realistic seasonal variations and intentional August 2023 dip for test queries)
INSERT INTO orders (id, customer_id, order_date, total_amount, status, shipping_city) VALUES
-- Jan 2023
(101, 1, '2023-01-15', 52998.00, 'completed', 'Mumbai'),
(102, 3, '2023-01-22', 7999.00, 'completed', 'Delhi'),
-- Feb 2023
(103, 2, '2023-02-18', 11499.00, 'completed', 'Mumbai'),
(104, 4, '2023-02-25', 18999.00, 'completed', 'Bangalore'),
-- Mar 2023
(105, 5, '2023-03-12', 4599.00, 'completed', 'Jaipur'),
(106, 1, '2023-03-29', 16098.00, 'completed', 'Mumbai'),
-- Apr 2023
(107, 6, '2023-04-10', 8999.00, 'completed', 'Pune'),
(108, 7, '2023-04-24', 3999.00, 'completed', 'Kochi'),
-- May 2023
(109, 8, '2023-05-15', 44999.00, 'completed', 'Mumbai'),
(110, 4, '2023-05-28', 5498.00, 'completed', 'Bangalore'),
-- Jun 2023
(111, 9, '2023-06-14', 7999.00, 'completed', 'Kolkata'),
(112, 10, '2023-06-28', 11499.00, 'completed', 'Bangalore'),
-- Jul 2023 (High peak month before drop)
(113, 11, '2023-07-08', 52998.00, 'completed', 'Delhi'),
(114, 2, '2023-07-16', 44999.00, 'completed', 'Mumbai'),
(115, 12, '2023-07-24', 18999.00, 'completed', 'Hyderabad'),
-- Aug 2023 (Noticeable drop in revenue: fewer high-ticket electronics, mostly smaller apparel & book orders)
(116, 13, '2023-08-05', 1499.00, 'completed', 'Mumbai'),
(117, 3, '2023-08-14', 899.00, 'completed', 'Delhi'),
(118, 5, '2023-08-22', 2499.00, 'completed', 'Jaipur'),
-- Sep 2023 (Recovery)
(119, 14, '2023-09-08', 22998.00, 'completed', 'Pune'),
(120, 8, '2023-09-21', 44999.00, 'completed', 'Mumbai'),
-- Oct 2023 (Festive season surge)
(121, 15, '2023-10-09', 52998.00, 'completed', 'Ahmedabad'),
(122, 1, '2023-10-18', 63998.00, 'completed', 'Mumbai'),
(123, 4, '2023-10-27', 37998.00, 'completed', 'Bangalore'),
-- Nov 2023
(124, 10, '2023-11-11', 11499.00, 'completed', 'Bangalore'),
(125, 2, '2023-11-20', 16098.00, 'completed', 'Mumbai'),
-- Dec 2023
(126, 7, '2023-12-12', 26998.00, 'completed', 'Kochi'),
(127, 3, '2023-12-25', 44999.00, 'completed', 'Delhi'),
-- Jan 2024
(128, 8, '2024-01-14', 52998.00, 'completed', 'Mumbai'),
(129, 11, '2024-01-28', 18999.00, 'completed', 'Delhi');

-- Order Items
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(101, 1, 1, 44999.00),
(101, 2, 1, 7999.00),
(102, 2, 1, 7999.00),
(103, 4, 1, 11499.00),
(104, 9, 1, 18999.00),
(105, 3, 1, 4599.00),
(106, 3, 1, 4599.00),
(106, 4, 1, 11499.00),
(107, 5, 1, 8999.00),
(108, 10, 1, 3999.00),
(109, 1, 1, 44999.00),
(110, 6, 2, 1499.00),
(110, 7, 1, 2499.00),
(111, 2, 1, 7999.00),
(112, 4, 1, 11499.00),
(113, 1, 1, 44999.00),
(113, 2, 1, 7999.00),
(114, 1, 1, 44999.00),
(115, 9, 1, 18999.00),
(116, 6, 1, 1499.00),
(117, 12, 1, 899.00),
(118, 7, 1, 2499.00),
(119, 4, 2, 11499.00),
(120, 1, 1, 44999.00),
(121, 1, 1, 44999.00),
(121, 2, 1, 7999.00),
(122, 1, 1, 44999.00),
(122, 9, 1, 18999.00),
(123, 9, 2, 18999.00),
(124, 4, 1, 11499.00),
(125, 3, 1, 4599.00),
(125, 4, 1, 11499.00),
(126, 2, 1, 7999.00),
(126, 9, 1, 18999.00),
(127, 1, 1, 44999.00),
(128, 1, 1, 44999.00),
(128, 2, 1, 7999.00),
(129, 9, 1, 18999.00);

-- Payments
INSERT INTO payments (order_id, payment_method, payment_status, amount, payment_date) VALUES
(101, 'Credit Card', 'captured', 52998.00, '2023-01-15 14:22:00'),
(102, 'UPI', 'captured', 7999.00, '2023-01-22 18:30:00'),
(103, 'Net Banking', 'captured', 11499.00, '2023-02-18 11:15:00'),
(104, 'Credit Card', 'captured', 18999.00, '2023-02-25 16:40:00'),
(105, 'UPI', 'captured', 4599.00, '2023-03-12 19:10:00'),
(106, 'Credit Card', 'captured', 16098.00, '2023-03-29 20:05:00'),
(107, 'UPI', 'captured', 8999.00, '2023-04-10 13:50:00'),
(108, 'Cash on Delivery', 'captured', 3999.00, '2023-04-24 15:30:00'),
(109, 'Credit Card', 'captured', 44999.00, '2023-05-15 12:00:00'),
(110, 'UPI', 'captured', 5498.00, '2023-05-28 17:45:00'),
(111, 'Net Banking', 'captured', 7999.00, '2023-06-14 10:20:00'),
(112, 'Credit Card', 'captured', 11499.00, '2023-06-28 21:10:00'),
(113, 'Credit Card', 'captured', 52998.00, '2023-07-08 14:15:00'),
(114, 'UPI', 'captured', 44999.00, '2023-07-16 19:00:00'),
(115, 'Credit Card', 'captured', 18999.00, '2023-07-24 15:30:00'),
(116, 'UPI', 'captured', 1499.00, '2023-08-05 18:20:00'),
(117, 'UPI', 'captured', 899.00, '2023-08-14 11:40:00'),
(118, 'Net Banking', 'captured', 2499.00, '2023-08-22 16:10:00'),
(119, 'Credit Card', 'captured', 22998.00, '2023-09-08 17:35:00'),
(120, 'Credit Card', 'captured', 44999.00, '2023-09-21 12:50:00'),
(121, 'Credit Card', 'captured', 52998.00, '2023-10-09 19:40:00'),
(122, 'Credit Card', 'captured', 63998.00, '2023-10-18 20:15:00'),
(123, 'Net Banking', 'captured', 37998.00, '2023-10-27 15:10:00'),
(124, 'UPI', 'captured', 11499.00, '2023-11-11 14:00:00'),
(125, 'Credit Card', 'captured', 16098.00, '2023-11-20 18:30:00'),
(126, 'Credit Card', 'captured', 26998.00, '2023-12-12 11:25:00'),
(127, 'Credit Card', 'captured', 44999.00, '2023-12-25 16:45:00'),
(128, 'Credit Card', 'captured', 52998.00, '2024-01-14 13:10:00'),
(129, 'Net Banking', 'captured', 18999.00, '2024-01-28 17:00:00');

-- Reset sequences to prevent key collisions
SELECT setval(pg_get_serial_sequence('customers', 'id'), COALESCE(MAX(id), 1)) FROM customers;
SELECT setval(pg_get_serial_sequence('products', 'id'), COALESCE(MAX(id), 1)) FROM products;
SELECT setval(pg_get_serial_sequence('orders', 'id'), COALESCE(MAX(id), 1)) FROM orders;
SELECT setval(pg_get_serial_sequence('order_items', 'id'), COALESCE(MAX(id), 1)) FROM order_items;
SELECT setval(pg_get_serial_sequence('payments', 'id'), COALESCE(MAX(id), 1)) FROM payments;

-- =================================================================
-- SECURITY: CREATE DEDICATED READ-ONLY ROLE FOR AI AGENT
-- =================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'readonly_agent') THEN
        CREATE ROLE readonly_agent WITH LOGIN PASSWORD 'readonly_secure_pass';
    END IF;
END
$$;

-- Grant SELECT only
GRANT CONNECT ON DATABASE ecommerce_db TO readonly_agent;
GRANT USAGE ON SCHEMA public TO readonly_agent;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_agent;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_agent;

-- Explicitly revoke write & DDL permissions
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM readonly_agent;
REVOKE CREATE ON SCHEMA public FROM readonly_agent;
