#DDL COMMANDS
-- ================================
-- STRONG ENTITIES
-- ================================

CREATE TABLE Customer (
    customer_id INT PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100) UNIQUE
);

-- Multivalued attribute: phone_no
CREATE TABLE CustomerPhone (
    customer_id INT,
    phone_no VARCHAR(15),
    PRIMARY KEY (customer_id, phone_no),
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE CASCADE
);

CREATE TABLE Category (
    category_id INT PRIMARY KEY,
    category_name VARCHAR(100),
    description TEXT,
    category_image VARCHAR(255),
    parent_category_id INT,
    FOREIGN KEY (parent_category_id) REFERENCES Category(category_id)
        ON DELETE SET NULL   -- Recursive relationship (subcategory → category)
);

ALTER TABLE Category
ADD COLUMN created_date DATE,
ADD COLUMN updated_date DATE;

ALTER TABLE Category
MODIFY created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
MODIFY updated_date DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;


CREATE TABLE Store (
    store_id INT PRIMARY KEY,
    store_name VARCHAR(100),
    opening_hours VARCHAR(100),
    website_url VARCHAR(255),
    street VARCHAR(100),
    city VARCHAR(100),
    state VARCHAR(100)
);

ALTER TABLE Store
ADD COLUMN pincode VARCHAR(10);

ALTER TABLE Store
MODIFY pincode VARCHAR(10) NOT NULL;


-- Multivalued attribute: contact number
CREATE TABLE StoreContact (
    store_id INT,
    contact_number VARCHAR(15),
    PRIMARY KEY (store_id, contact_number),
    FOREIGN KEY (store_id) REFERENCES Store(store_id) ON DELETE CASCADE
);

CREATE TABLE Product (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(100),
    description TEXT,
    brand VARCHAR(50),
    min_price DECIMAL(10,2),
    max_price DECIMAL(10,2),
    category_id INT,
    FOREIGN KEY (category_id) REFERENCES Category(category_id)
);

-- Multivalued attribute: tags
CREATE TABLE ProductTag (
    product_id INT,
    tag VARCHAR(50),
    PRIMARY KEY (product_id, tag),
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE
);

CREATE TABLE Wishlist (
    wishlist_id INT PRIMARY KEY,
    wishlist_name VARCHAR(100),
    created_on DATE,
    last_updated DATE,
    customer_id INT,
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
        ON DELETE CASCADE
);

-- M:N relationship between Wishlist and Product
CREATE TABLE WishlistProduct (
    wishlist_id INT,
    product_id INT,
    PRIMARY KEY (wishlist_id, product_id),
    FOREIGN KEY (wishlist_id) REFERENCES Wishlist(wishlist_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE
);

CREATE TABLE PriceAlert (
    alert_id INT PRIMARY KEY,
    target_price DECIMAL(10,2),
    alert_date DATE,
    status VARCHAR(50),
    notification_type VARCHAR(50),
    product_id INT,
    customer_id INT,
    FOREIGN KEY (product_id) REFERENCES Product(product_id),
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
);

ALTER TABLE PriceAlert
ADD COLUMN store_id INT,
ADD CONSTRAINT fk_pricealert_store
    FOREIGN KEY (store_id) REFERENCES Store(store_id)
    ON DELETE CASCADE;


-- WEAK ENTITY: Inventory (depends on Product + Store)
CREATE TABLE Inventory (
    inventory_id INT,
    product_id INT,
    store_id INT,
    quantity INT,
    last_updated DATE,
    PRIMARY KEY (inventory_id, product_id, store_id),
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE,
    FOREIGN KEY (store_id) REFERENCES Store(store_id) ON DELETE CASCADE
);

ALTER TABLE Inventory
ADD COLUMN price_in_store DECIMAL(10,2),
ADD COLUMN delivery_options VARCHAR(100),
ADD COLUMN discount DECIMAL(5,2);

# DDL COMMANDS
customer:
INSERT INTO Customer VALUES
(1, 'Anika', 'P', 'anika@example.com'),
(2, 'Ravi', 'Kumar', 'ravi@example.com'),
(3, 'Sneha', 'Sharma', 'sneha@example.com'),
(4, 'Amit', 'Rao', 'amit@example.com'),
(5, 'Priya', 'Menon', 'priya@example.com');

CustomerPhone (multivalued):
INSERT INTO CustomerPhone VALUES
(1, '9876543210'), (1, '9123456789'),
(2, '9988776655'),
(3, '9012345678'),
(4, '9090909090'),
(5, '8888888888');

Category (recursive + date fields):
INSERT INTO Category VALUES
(1, 'Electronics', 'Electronic gadgets', 'electronics.jpg', NULL, '2025-09-01', '2025-10-12'),
(2, 'Mobiles', 'Smartphones and accessories', 'mobiles.jpg', 1, '2025-09-02', '2025-10-12'),
(3, 'Laptops', 'Personal computers', 'laptops.jpg', 1, '2025-09-03', '2025-10-12'),
(4, 'Fashion', 'Clothing and accessories', 'fashion.jpg', NULL, '2025-09-04', '2025-10-12'),
(5, 'Shoes', 'Footwear and sports shoes', 'shoes.jpg', 4, '2025-09-05', '2025-10-12');

Store (with pincode):
INSERT INTO Store VALUES
(1, 'TechWorld', '9AM - 9PM', 'www.techworld.com', 'MG Road', 'Bengaluru', 'Karnataka', '560001'),
(2, 'GadgetHub', '10AM - 8PM', 'www.gadgethub.com', 'Anna Nagar', 'Chennai', 'Tamil Nadu', '600040'),
(3, 'MegaMart', '8AM - 10PM', 'www.megamart.com', 'DLF Phase 2', 'Gurugram', 'Haryana', '122002'),
(4, 'UrbanStyle', '10AM - 9PM', 'www.urbanstyle.com', 'Linking Road', 'Mumbai', 'Maharashtra', '400050'),
(5, 'ShoePlanet', '9AM - 10PM', 'www.shoeplanet.com', 'Park Street', 'Kolkata', 'West Bengal', '700016');

StoreContact (multivalued):
INSERT INTO StoreContact VALUES
(1, '0801234567'), (1, '0809876543'),
(2, '0448765432'),
(3, '0119988776'),
(4, '0227654321'),
(5, '0332345678');

Product:
INSERT INTO Product VALUES
(101, 'Smartphone X', 'Latest 5G Android phone', 'BrandX', 15000.00, 25000.00, 2),
(102, 'Laptop Pro', 'High performance business laptop', 'CompTech', 55000.00, 80000.00, 3),
(103, 'Casual Shirt', 'Cotton shirt for men', 'FabWear', 800.00, 1200.00, 4),
(104, 'Running Shoes', 'Comfortable sports running shoes', 'Speedo', 3000.00, 5000.00, 5),
(105, 'Wireless Earbuds', 'Noise-cancelling Bluetooth earbuds', 'SoundMax', 2000.00, 4000.00, 2);

ProductTag (multivalued):
INSERT INTO ProductTag VALUES
(101, 'phone'), (101, 'android'),
(102, 'laptop'), (102, 'electronics'),
(103, 'shirt'), (103, 'clothing'),
(104, 'footwear'), (104, 'sports'),
(105, 'audio'), (105, 'wireless');

Wishlist:
INSERT INTO Wishlist VALUES
(501, 'Anika Favorites', '2025-10-01', '2025-10-12', 1),
(502, 'Tech Picks', '2025-09-01', '2025-10-10', 2),
(503, 'Sneha Wishlist', '2025-09-15', '2025-10-05', 3),
(504, 'Amit Essentials', '2025-09-20', '2025-10-09', 4),
(505, 'Priya Collection', '2025-09-25', '2025-10-11', 5);

WishlistProduct (M:N):
INSERT INTO WishlistProduct VALUES
(501, 101), (501, 105),
(502, 102),
(503, 103),
(504, 104),
(505, 101), (505, 103);

PriceAlert (with new store_id foreign key):
INSERT INTO PriceAlert VALUES
(1001, 18000.00, '2025-10-12', 'active', 'email', 101, 1, 1),
(1002, 75000.00, '2025-10-11', 'active', 'sms', 102, 2, 1),
(1003, 1000.00, '2025-10-10', 'inactive', 'app', 103, 3, 4),
(1004, 3500.00, '2025-10-08', 'active', 'email', 104, 4, 5),
(1005, 2500.00, '2025-10-09', 'active', 'email', 105, 5, 2);

Inventory (weak entity with new attributes):
INSERT INTO Inventory VALUES
(1, 101, 1, 20, '2025-10-10', 19000.00, 'Home Delivery', 10.00),
(2, 102, 1, 15, '2025-10-11', 72000.00, 'Pickup', 5.00),
(3, 103, 4, 30, '2025-10-09', 950.00, 'Both', 0.00),
(4, 104, 5, 25, '2025-10-08', 4000.00, 'Home Delivery', 8.00),
(5, 105, 2, 40, '2025-10-07', 2800.00, 'Both', 12.00);

# Triggers
1. Auto-update PriceAlert status when price drops

DELIMITER //
CREATE TRIGGER trigger_price_alert
AFTER UPDATE ON Inventory
FOR EACH ROW
BEGIN
    UPDATE PriceAlert
    SET status = 'triggered'
    WHERE product_id = NEW.product_id
      AND store_id = NEW.store_id
      AND target_price >= NEW.price_in_store
      AND status = 'active';
END //
DELIMITER ;

2. Auto-log every price change

CREATE TABLE PriceHistory (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    store_id INT,
    old_price DECIMAL(10,2),
    new_price DECIMAL(10,2),
    changed_on DATETIME DEFAULT CURRENT_TIMESTAMP
);

DELIMITER //
CREATE TRIGGER track_price_change
BEFORE UPDATE ON Inventory
FOR EACH ROW
BEGIN
    IF OLD.price_in_store <> NEW.price_in_store THEN
        INSERT INTO PriceHistory(product_id, store_id, old_price, new_price)
        VALUES (OLD.product_id, OLD.store_id, OLD.price_in_store, NEW.price_in_store);
    END IF;
END //
DELIMITER ;

3. Update last_updated timestamps automatically
DELIMITER //
CREATE TRIGGER update_inventory_timestamp
BEFORE UPDATE ON Inventory
FOR EACH ROW
BEGIN
    SET NEW.last_updated = CURRENT_DATE;
END //
DELIMITER ;

4. Add a trigger to prevent negative inventory:
DELIMITER //
CREATE TRIGGER prevent_negative_stock
BEFORE UPDATE ON Inventory
FOR EACH ROW
BEGIN
    IF NEW.quantity < 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Inventory quantity cannot be negative';
    END IF;
END //
DELIMITER ;

5. Update Product min/max prices automatically:
DELIMITER //
CREATE TRIGGER update_product_price_range
AFTER INSERT ON Inventory
FOR EACH ROW
BEGIN
    UPDATE Product
    SET min_price = (SELECT MIN(price_in_store) FROM Inventory WHERE product_id = NEW.product_id),
        max_price = (SELECT MAX(price_in_store) FROM Inventory WHERE product_id = NEW.product_id)
    WHERE product_id = NEW.product_id;
END //
DELIMITER ;

# Procedures
1. Compare store prices for a product

CALL ComparePrices(101);

DELIMITER //

CREATE PROCEDURE ComparePrices(IN p_product_id INT)
BEGIN
    SELECT 
        s.store_name, 
        i.price_in_store,
        i.discount
    FROM Inventory i
    JOIN Store s ON i.store_id = s.store_id
    WHERE i.product_id = p_product_id;
END //

DELIMITER ;

2. Add new product + initial stock in one go

DROP PROCEDURE IF EXISTS AddNewProduct;

DELIMITER //
CREATE PROCEDURE AddNewProduct(
    IN pname VARCHAR(100),
    IN descp TEXT,
    IN brand VARCHAR(50),
    IN cat_id INT,
    IN store_id INT,
    IN qty INT,
    IN price DECIMAL(10,2)
)
BEGIN
    DECLARE new_pid INT;
    DECLARE new_inv_id INT;
    
    SET new_pid = (SELECT IFNULL(MAX(product_id), 100) + 1 FROM Product);
    SET new_inv_id = (SELECT IFNULL(MAX(inventory_id), 0) + 1 FROM Inventory);
    
    INSERT INTO Product(product_id, product_name, description, brand, min_price, max_price, category_id)
    VALUES (new_pid, pname, descp, brand, price, price, cat_id);
    
    INSERT INTO Inventory(inventory_id, product_id, store_id, quantity, last_updated, price_in_store, discount)
    VALUES (new_inv_id, new_pid, store_id, qty, CURRENT_DATE, price, 0);
END //
DELIMITER ;

3. Auto-restock popular items

DELIMITER //
CREATE PROCEDURE AutoRestock()
BEGIN
    UPDATE Inventory
    SET quantity = quantity + 10
    WHERE quantity < 5;
END //
DELIMITER ;

4. Add a procedure to get triggered alerts:
DELIMITER //
CREATE PROCEDURE GetTriggeredAlerts(IN cust_id INT)
BEGIN
    SELECT pa.alert_id, p.product_name, s.store_name, 
           pa.target_price, i.price_in_store, pa.alert_date
    FROM PriceAlert pa
    JOIN Product p ON pa.product_id = p.product_id
    JOIN Store s ON pa.store_id = s.store_id
    JOIN Inventory i ON pa.product_id = i.product_id AND pa.store_id = i.store_id
    WHERE pa.customer_id = cust_id AND pa.status = 'triggered'
    ORDER BY pa.alert_date DESC;
END //
DELIMITER ;

5. Add a procedure to find best deals:
DELIMITER //
CREATE PROCEDURE GetBestDeals(IN discount_threshold DECIMAL(5,2))
BEGIN
    SELECT p.product_name, s.store_name, i.price_in_store, i.discount
    FROM Inventory i
    JOIN Product p ON i.product_id = p.product_id
    JOIN Store s ON i.store_id = s.store_id
    WHERE i.discount >= discount_threshold
    ORDER BY i.discount DESC;
END //
DELIMITER ;

# Functions
1. Calculate discounted price for a product in a store

DELIMITER //
CREATE FUNCTION GetDiscountedPrice(pid INT, sid INT)
RETURNS DECIMAL(10,2)
DETERMINISTIC
BEGIN
    DECLARE base_price DECIMAL(10,2) DEFAULT 0;
    DECLARE discount DECIMAL(5,2) DEFAULT 0;

    SELECT COALESCE(price_in_store, 0), COALESCE(discount, 0)
    INTO base_price, discount
    FROM Inventory
    WHERE product_id = pid AND store_id = sid
    LIMIT 1;

    RETURN base_price - (base_price * discount / 100);
END //
DELIMITER ;

2. Calculate average discount for a category

DELIMITER //
CREATE FUNCTION CategoryAvgDiscount(cid INT)
RETURNS DECIMAL(5,2)
DETERMINISTIC
BEGIN
    DECLARE avg_discount DECIMAL(5,2);
    SELECT AVG(discount) INTO avg_discount
    FROM Inventory i
    JOIN Product p ON i.product_id = p.product_id
    WHERE p.category_id = cid;
    RETURN avg_discount;
END //
DELIMITER ;

3. Function to compute product availability

DELIMITER //
CREATE FUNCTION IsProductAvailable(pid INT)
RETURNS VARCHAR(10)
DETERMINISTIC
BEGIN
    DECLARE total_qty INT;
    SELECT SUM(quantity) INTO total_qty FROM Inventory WHERE product_id = pid;
    RETURN IF(total_qty > 0, 'Available', 'Out of Stock');
END //
DELIMITER ;

4. Check if price is at lowest point:
DELIMITER //
CREATE FUNCTION IsLowestPrice(pid INT, sid INT)
RETURNS VARCHAR(3)
DETERMINISTIC
BEGIN
    DECLARE current_price DECIMAL(10,2);
    DECLARE min_price DECIMAL(10,2);
    
    SELECT price_in_store INTO current_price
    FROM Inventory
    WHERE product_id = pid AND store_id = sid;
    
    SELECT MIN(price_in_store) INTO min_price
    FROM Inventory
    WHERE product_id = pid;
    
    RETURN IF(current_price = min_price, 'Yes', 'No');
END //
DELIMITER ;


TESTING:
1.	DROP FUNCTION IF EXISTS IsProductAvailable;
   	DELIMITER //
	CREATE FUNCTION IsProductAvailable(pid INT)
	RETURNS VARCHAR(15)
	DETERMINISTIC
	BEGIN
    	DECLARE total_qty INT;
    	SELECT SUM(quantity)
    	INTO total_qty
    	FROM Inventory
    	WHERE product_id = pid;
    	RETURN IF(total_qty > 0, 'Available', 'Out of Stock');
	END //
	DELIMITER ;
	
	SELECT product_id, product_name FROM Product;

	SELECT IsProductAvailable(101) AS availability_101;

# Grants
GRANT SELECT, INSERT, UPDATE ON mini_project.Customer TO 'ravi'@'localhost' IDENTIFIED BY 'ravi_password';