-- MySQL seed schema and data for NL2SQL demo
CREATE DATABASE IF NOT EXISTS nl2sql_target;
USE nl2sql_target;

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS categories;

CREATE TABLE customers (
  customer_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE,
  join_date DATE,
  country VARCHAR(64),
  total_spent DECIMAL(12,2) DEFAULT 0
);

CREATE TABLE categories (
  category_id INT PRIMARY KEY AUTO_INCREMENT,
  category_name VARCHAR(255) NOT NULL,
  description TEXT
);

CREATE TABLE products (
  product_id INT PRIMARY KEY AUTO_INCREMENT,
  product_name VARCHAR(255) NOT NULL,
  category_id INT,
  price DECIMAL(10,2) NOT NULL,
  stock_quantity INT DEFAULT 0,
  FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE orders (
  order_id INT PRIMARY KEY AUTO_INCREMENT,
  customer_id INT,
  order_date DATE,
  status VARCHAR(50),
  total_amount DECIMAL(12,2),
  FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_items (
  order_item_id INT PRIMARY KEY AUTO_INCREMENT,
  order_id INT,
  product_id INT,
  quantity INT NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL,
  FOREIGN KEY (order_id) REFERENCES orders(order_id),
  FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Sample data
INSERT INTO categories (category_name, description) VALUES
 ('Electronics','Electronic gadgets'),
 ('Books','Printed and digital books'),
 ('Home','Home and kitchen');

INSERT INTO customers (name, email, join_date, country, total_spent) VALUES
 ('Alice Smith','alice@example.com','2023-01-10','USA',1200.00),
 ('Bob Lee','bob@example.com','2023-03-15','India',800.00),
 ('Carlos Diaz','carlos@example.com','2023-06-05','Spain',450.00);

INSERT INTO products (product_name, category_id, price, stock_quantity) VALUES
 ('Smartphone', 1, 699.99, 50),
 ('Laptop', 1, 1299.00, 20),
 ('Cookbook', 2, 25.50, 200),
 ('Blender', 3, 89.00, 80);

INSERT INTO orders (customer_id, order_date, status, total_amount) VALUES
 (1,'2024-01-10','shipped',725.49),
 (2,'2024-02-05','processing',178.00),
 (1,'2024-03-12','delivered',1299.00);

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
 (1,1,1,699.99),
 (1,3,1,25.50),
 (2,4,2,89.00),
 (3,2,1,1299.00);
