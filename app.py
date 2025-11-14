from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from mysql.connector import Error
from math import ceil
from functools import wraps
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_in_production'

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Change to your MySQL user
    'password': 'Anishm60',  # <-- Make sure this is your correct password
    'database': 'mini_project'
}

# Database connection helper
def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== AUTH ROUTES ====================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        role = request.form.get('role')

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Customer WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user:
                session['user_id'] = user['customer_id']
                session['user_name'] = f"{user['first_name']} {user['last_name']}"

                # --- Check admin flag from database ---
                is_admin = user.get('is_admin', False)

                # --- If user selected Admin ---
                if role == 'admin':
                    if is_admin:
                        session['role'] = 'admin'
                        flash(f"Welcome Admin {session['user_name']}!", "success")
                        return redirect(url_for('admin_dashboard'))
                    else:
                        flash("Access denied: You are not an admin.", "danger")
                        return redirect(url_for('login'))

                # --- If user selected Customer ---
                else:
                    session['role'] = 'customer'
                    flash(f"Welcome {session['user_name']}!", "success")

                    # ================================================================
                    # POP-UP NOTIFICATION LOGIC - Checks for alerts on login
                    # ================================================================
                    try:
                        customer_id = session['user_id']
                        alert_ids_to_update = []

                        # 1. Find triggered alerts
                        cursor.execute("""
                            SELECT pa.alert_id, pa.target_price, p.product_name, s.store_name, i.price_in_store
                            FROM PriceAlert pa
                            JOIN Product p ON pa.product_id = p.product_id
                            JOIN Store s ON pa.store_id = s.store_id
                            LEFT JOIN Inventory i ON pa.product_id = i.product_id AND pa.store_id = i.store_id
                            WHERE pa.customer_id = %s AND pa.status = 'triggered'
                        """, (customer_id,))
                        triggered_alerts = cursor.fetchall()

                        if triggered_alerts:
                            # Convert price strings to floats before saving
                            for alert in triggered_alerts:
                                if alert['target_price'] is not None:
                                    alert['target_price'] = float(alert['target_price'])
                                if alert['price_in_store'] is not None:
                                    alert['price_in_store'] = float(alert['price_in_store'])

                            session['triggered_alerts'] = triggered_alerts
                            alert_ids_to_update = [alert['alert_id'] for alert in triggered_alerts]

                            # Mark them as 'viewed' in the database
                            if alert_ids_to_update:
                                format_strings = ','.join(['%s'] * len(alert_ids_to_update))
                                cursor.execute(f"""
                                    UPDATE PriceAlert SET status = 'viewed'
                                    WHERE alert_id IN ({format_strings})
                                """, tuple(alert_ids_to_update))
                                conn.commit()
                    except Error as e:
                        print(f"Error checking alerts: {e}")
                        # Don’t block login if alert check fails
                    # ================================================================
                    # END POP-UP NOTIFICATION LOGIC
                    # ================================================================
                    return redirect(url_for('customer_home'))

            else:
                flash('Invalid credentials. Please check your email.', 'danger')

            cursor.close()
            conn.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))

# ==================== CUSTOMER ROUTES ====================

@app.route('/customer/home')
@login_required
def customer_home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # --- Get filters and pagination from URL ---
    category_id = request.args.get('category_id', type=int)
    sort_key = request.args.get('sort', 'name_asc')  # Default sort
    page = request.args.get('page', 1, type=int)      # Current page
    per_page = 5                                      # Products per page
    offset = (page - 1) * per_page
    
    # --- Sorting whitelist ---
    sort_options = {
        'name_asc': 'p.product_name ASC',
        'price_asc': 'MIN(i.price_in_store) ASC',
        'price_desc': 'MIN(i.price_in_store) DESC'
    }
    order_by_clause = sort_options.get(sort_key, 'p.product_name ASC')
    
    # --- Count total products for pagination ---
    count_query = "SELECT COUNT(*) as total FROM Product p"
    count_params = []
    if category_id:
        count_query += " JOIN Category c ON p.category_id = c.category_id WHERE c.category_id = %s OR c.parent_category_id = %s"
        count_params.extend([category_id, category_id])
    cursor.execute(count_query, count_params)
    total_products = cursor.fetchone()['total']
    total_pages = (total_products + per_page - 1) // per_page  # Ceiling division
    
    # --- Main query with LIMIT/OFFSET ---
    query = """
        SELECT p.product_id, p.product_name, p.brand, p.description,
               p.image_url, 
               c.category_name,
               MIN(i.price_in_store) as best_price,
               MAX(i.discount) as max_discount
        FROM Product p
        JOIN Category c ON p.category_id = c.category_id
        LEFT JOIN Inventory i ON p.product_id = i.product_id
    """
    params = []
    if category_id:
        query += " WHERE c.category_id = %s OR c.parent_category_id = %s"
        params.extend([category_id, category_id])
    
    query += f"""
        GROUP BY p.product_id, p.product_name, p.brand, p.description, p.image_url, c.category_name
        ORDER BY {order_by_clause}
        LIMIT %s OFFSET %s
    """
    params.extend([per_page, offset])
    
    cursor.execute(query, params)
    products = cursor.fetchall()
    
    # --- Categories for sidebar ---
    cursor.execute("SELECT * FROM Category WHERE parent_category_id IS NULL")
    categories = cursor.fetchall()
    
    # --- POP-UP MODAL logic ---
    triggered_alerts = session.pop('triggered_alerts', None)
    
    cursor.close()
    conn.close()
    
    return render_template(
        'customer_home.html', 
        products=products, 
        categories=categories,
        selected_category=category_id,
        selected_sort=sort_key,
        triggered_alerts=triggered_alerts,
        page=page,
        total_pages=total_pages
    )


@app.route('/customer/product/<int:product_id>')
@login_required
def customer_product_detail(product_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get product details
    cursor.execute("""
        SELECT p.*, c.category_name
        FROM Product p
        JOIN Category c ON p.category_id = c.category_id
        WHERE p.product_id = %s
    """, (product_id,))
    product = cursor.fetchone()
    
    # Call ComparePrices procedure
    cursor.callproc('ComparePrices', [product_id])
    
    # Fetch results from procedure
    store_prices = []
    for result in cursor.stored_results():
        store_prices = result.fetchall()
    
    # Determine availability based on quantity in inventory
    cursor.execute("""
        SELECT SUM(quantity) AS total_quantity
        FROM Inventory
        WHERE product_id = %s
    """, (product_id,))
    total_qty = cursor.fetchone()['total_quantity'] or 0

    availability = "Available" if total_qty > 0 else "Out of Stock"
    
    # Get price history
    cursor.execute("""
        SELECT old_price, new_price, changed_on,
               (new_price - old_price) as price_change
        FROM PriceHistory
        WHERE product_id = %s
        ORDER BY changed_on DESC
        LIMIT 5
    """, (product_id,))
    price_history = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('customer_product_detail.html', 
                           product=product, 
                           store_prices=store_prices,
                           availability=availability,
                           price_history=price_history)



@app.route('/customer/wishlist')
@login_required
def customer_wishlist():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    customer_id = session['user_id']
    
    # Join query to get wishlist items
    cursor.execute("""
        SELECT w.wishlist_id, w.wishlist_name, w.created_on, w.last_updated,
               p.product_id, p.product_name, p.brand,
               MIN(i.price_in_store) as best_price
        FROM Wishlist w
        LEFT JOIN WishlistProduct wp ON w.wishlist_id = wp.wishlist_id
        LEFT JOIN Product p ON wp.product_id = p.product_id
        LEFT JOIN Inventory i ON p.product_id = i.product_id
        WHERE w.customer_id = %s
        GROUP BY w.wishlist_id, w.wishlist_name, w.created_on, w.last_updated,
                 p.product_id, p.product_name, p.brand
    """, (customer_id,))
    wishlist_items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('customer_wishlist.html', wishlist_items=wishlist_items)

@app.route('/customer/add_to_wishlist', methods=['POST'])
@login_required
def add_to_wishlist():
    product_id = request.form.get('product_id')
    customer_id = session['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get or create default wishlist
    cursor.execute("""
        SELECT wishlist_id FROM Wishlist 
        WHERE customer_id = %s 
        LIMIT 1
    """, (customer_id,))
    
    result = cursor.fetchone()
    
    if result:
        wishlist_id = result[0]
    else:
        # Create new wishlist
        cursor.execute("""
            SELECT IFNULL(MAX(wishlist_id), 500) + 1 as new_id 
            FROM Wishlist
        """)
        wishlist_id = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO Wishlist (wishlist_id, wishlist_name, created_on, last_updated, customer_id)
            VALUES (%s, %s, CURDATE(), CURDATE(), %s)
        """, (wishlist_id, f"{session['user_name']}'s Wishlist", customer_id))
    
    # Add product to wishlist
    try:
        cursor.execute("""
            INSERT INTO WishlistProduct (wishlist_id, product_id)
            VALUES (%s, %s)
        """, (wishlist_id, product_id))
        conn.commit()
        flash('Product added to wishlist!', 'success')
    except Error:
        flash('Product already in wishlist', 'warning')
    
    cursor.close()
    conn.close()
    
    return redirect(request.referrer)

@app.route('/customer/remove_from_wishlist/<int:wishlist_id>/<int:product_id>')
@login_required
def remove_from_wishlist(wishlist_id, product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM WishlistProduct 
        WHERE wishlist_id = %s AND product_id = %s
    """, (wishlist_id, product_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Product removed from wishlist', 'info')
    return redirect(url_for('customer_wishlist'))

@app.route('/customer/alerts')
@login_required
def customer_alerts():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    customer_id = session['user_id']
    
    cursor.execute("""
        SELECT pa.alert_id, pa.target_price, pa.alert_date, pa.status, pa.notification_type,
               pa.product_id,
               p.product_name, p.brand,
               s.store_name,
               i.price_in_store as current_price
        FROM PriceAlert pa
        JOIN Product p ON pa.product_id = p.product_id
        JOIN Store s ON pa.store_id = s.store_id
        LEFT JOIN Inventory i ON pa.product_id = i.product_id AND pa.store_id = i.store_id
        WHERE pa.customer_id = %s
        ORDER BY pa.alert_date DESC
    """, (customer_id,))
    alerts = cursor.fetchall()

    # ==================================================
    # THIS IS THE FIX (2 of 3)
    # Convert price strings to floats before rendering
    # ==================================================
    for alert in alerts:
        if alert['target_price'] is not None:
            alert['target_price'] = float(alert['target_price'])
        if alert['current_price'] is not None:
            alert['current_price'] = float(alert['current_price'])
    
    cursor.close()
    conn.close()
    
    return render_template('customer_alerts.html', alerts=alerts)

@app.route('/customer/set_alert', methods=['POST'])
@login_required
def set_alert():
    product_id = request.form.get('product_id')
    store_id = request.form.get('store_id')
    target_price = request.form.get('target_price')
    notification_type = request.form.get('notification_type', 'email')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT IFNULL(MAX(alert_id), 1000) + 1 as new_id FROM PriceAlert")
    alert_id = cursor.fetchone()[0]
    
    try:
        cursor.execute("""
            INSERT INTO PriceAlert 
            (alert_id, target_price, alert_date, status, notification_type, product_id, customer_id, store_id)
            VALUES (%s, %s, CURDATE(), 'active', %s, %s, %s, %s)
        """, (alert_id, target_price, notification_type, product_id, session['user_id'], store_id))
        
        conn.commit()
        flash('Price alert created!', 'success')
    except Error as e:
        flash(f'Error creating alert: {e}', 'danger')
    
    cursor.close()
    conn.close()
    
    return redirect(request.referrer)

@app.route('/customer/delete_alert/<int:alert_id>')
@login_required
def delete_alert(alert_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure the user only deletes their own alerts
    cursor.execute("""
        DELETE FROM PriceAlert 
        WHERE alert_id = %s AND customer_id = %s
    """, (alert_id, session['user_id']))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Price alert deleted', 'info')
    return redirect(url_for('customer_alerts'))

# ================================================================
# NEW EXPENSE TRACKER ROUTE 1: "BUY" BUTTON LOGIC
# ================================================================
@app.route('/customer/buy_product', methods=['POST'])
@login_required
def buy_product():
    try:
        customer_id = session['user_id']
        product_id = request.form.get('product_id')
        store_id = request.form.get('store_id')
        price_paid = request.form.get('price_paid')

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO Orders (customer_id, product_id, store_id, price_paid, purchase_date)
            VALUES (%s, %s, %s, %s, NOW())
        """, (customer_id, product_id, store_id, price_paid))
        
        conn.commit()
        
        # After buying, let's also reduce the stock quantity by 1
        cursor.execute("""
            UPDATE Inventory 
            SET quantity = quantity - 1
            WHERE product_id = %s AND store_id = %s AND quantity > 0
        """, (product_id, store_id))
        conn.commit()

        cursor.close()
        conn.close()
        
        flash(f'Purchase successful! Added to your expense tracker.', 'success')
        
    except Error as e:
        flash(f'An error occurred: {e}', 'danger')
        
    return redirect(request.referrer)

# ================================================================
# NEW EXPENSE TRACKER ROUTE 2: "MY EXPENSES" PAGE
# ================================================================
@app.route('/customer/expenses')
@login_required
def customer_expenses():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    customer_id = session['user_id']

    # Get total spending (Aggregate Query)
    cursor.execute("""
        SELECT SUM(price_paid) as total 
        FROM Orders 
        WHERE customer_id = %s
    """, (customer_id,))
    
    # ==================================================
    # THIS IS THE FIX (3 of 3)
    # Convert total_spent to float
    # ==================================================
    total_spent = cursor.fetchone()['total'] or 0
    total_spent = float(total_spent)

    # Get list of all expenses (Join Query)
    cursor.execute("""
        SELECT o.price_paid, o.purchase_date, p.product_name, s.store_name
        FROM Orders o
        LEFT JOIN Product p ON o.product_id = p.product_id
        LEFT JOIN Store s ON o.store_id = s.store_id
        WHERE o.customer_id = %s
        ORDER BY o.purchase_date DESC
    """, (customer_id,))
    expenses = cursor.fetchall()
    
    # And convert the price in the list
    for item in expenses:
        if item['price_paid'] is not None:
            item['price_paid'] = float(item['price_paid'])

    cursor.close()
    conn.close()
    
    return render_template('customer_expenses.html', 
                         expenses=expenses, 
                         total_spent=total_spent)


# ==================== ADMIN ROUTES ====================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Aggregate queries for dashboard
    cursor.execute("SELECT COUNT(*) as count FROM Customer")
    total_customers = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM Product")
    total_products = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM Store")
    total_stores = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM PriceAlert WHERE status = 'active'")
    active_alerts = cursor.fetchone()['count']
    
    cursor.execute("SELECT SUM(quantity) as total FROM Inventory")
    total_inventory = cursor.fetchone()['total'] or 0
    
    # Fetch price history for the chart's initial load
    cursor.execute("""
        SELECT new_price, DATE_FORMAT(changed_on, '%b %d, %H:%i') as short_time
        FROM PriceHistory
        ORDER BY changed_on DESC
        LIMIT 10
    """)
    # We must reverse it so the chart shows time from left-to-right
    recent_changes = list(reversed(cursor.fetchall())) 
    
    # Format data for Chart.js
    chart_labels = [change['short_time'] for change in recent_changes]
    # Also convert to float here
    chart_data = [float(change['new_price']) for change in recent_changes]

    cursor.close()
    conn.close()
    
    return render_template('admin_dashboard.html',
                         total_customers=total_customers,
                         total_products=total_products,
                         total_stores=total_stores,
                         active_alerts=active_alerts,
                         total_inventory=total_inventory,
                         # Pass chart data to the template
                         chart_labels=chart_labels, 
                         chart_data=chart_data)

@app.route('/admin/dashboard/data')
@admin_required
def admin_dashboard_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Aggregate queries
        cursor.execute("SELECT COUNT(*) as count FROM Customer")
        total_customers = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM Product")
        total_products = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM Store")
        total_stores = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM PriceAlert WHERE status = 'active'")
        active_alerts = cursor.fetchone()['count']
        cursor.execute("SELECT SUM(quantity) as total FROM Inventory")
        total_inventory = cursor.fetchone()['total'] or 0

        # Fetch fresh chart data
        cursor.execute("""
            SELECT new_price, DATE_FORMAT(changed_on, '%b %d, %H:%i') as short_time
            FROM PriceHistory
            ORDER BY changed_on DESC
            LIMIT 10
        """)
        recent_changes = list(reversed(cursor.fetchall())) # Reverse for chart
        
        chart_labels = [change['short_time'] for change in recent_changes]
        # Also convert to float here
        chart_data = [float(change['new_price']) for change in recent_changes]

        cursor.close()
        conn.close()
        
        return jsonify({
            'total_customers': total_customers,
            'total_products': total_products,
            'total_stores': total_stores,
            'active_alerts': active_alerts,
            'total_inventory': total_inventory,
            'chart_labels': chart_labels,
            'chart_data': chart_data
        })

    except Exception as e:
        print(f"Error in admin_dashboard_data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM Customer ORDER BY customer_id")
    users = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin_users.html', users=users)

@app.route('/admin/add_user', methods=['POST'])
@admin_required
def admin_add_user():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT IFNULL(MAX(customer_id), 0) + 1 as new_id FROM Customer")
    customer_id = cursor.fetchone()[0]
    
    try:
        cursor.execute("""
            INSERT INTO Customer (customer_id, first_name, last_name, email)
            VALUES (%s, %s, %s, %s)
        """, (customer_id, first_name, last_name, email))
        
        if phone:
            cursor.execute("""
                INSERT INTO CustomerPhone (customer_id, phone_no)
                VALUES (%s, %s)
            """, (customer_id, phone))
        
        conn.commit()
        flash('User added successfully!', 'success')
    except Error as e:
        flash(f'Error adding user: {e}', 'danger')

    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_user/<int:customer_id>')
@admin_required
def admin_delete_user(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM Customer WHERE customer_id = %s", (customer_id,))
        conn.commit()
        flash('User deleted successfully!', 'success')
    except Error as e:
        flash(f'Error deleting user: {e}', 'danger')
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_users'))

@app.route('/admin/inventory')
@admin_required
def admin_inventory():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT i.inventory_id, i.product_id, i.store_id, i.quantity, 
               i.last_updated, i.price_in_store, i.discount,
               p.product_name, s.store_name
        FROM Inventory i
        JOIN Product p ON i.product_id = p.product_id
        JOIN Store s ON i.store_id = s.store_id
        ORDER BY i.last_updated DESC
    """)
    inventory = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin_inventory.html', inventory=inventory)

@app.route('/admin/update_inventory', methods=['POST'])
@admin_required
def admin_update_inventory():
    inventory_id = request.form.get('inventory_id')
    product_id = request.form.get('product_id')
    store_id = request.form.get('store_id')
    quantity = request.form.get('quantity')
    price = request.form.get('price')
    discount = request.form.get('discount')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # This UPDATE will trigger the triggers
        cursor.execute("""
            UPDATE Inventory 
            SET quantity = %s, price_in_store = %s, discount = %s
            WHERE inventory_id = %s AND product_id = %s AND store_id = %s
        """, (quantity, price, discount, inventory_id, product_id, store_id))
        
        conn.commit()
        flash('Inventory updated! Triggers executed.', 'success')
    except Error as e:
        flash(f'Error updating inventory: {e}', 'danger')
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_inventory'))

@app.route('/admin/auto_restock')
@admin_required
def admin_auto_restock():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Call the AutoRestock procedure
        cursor.callproc('AutoRestock')
        conn.commit()
        flash('Auto-restock procedure executed!', 'success')
    except Error as e:
        flash(f'Error running auto-restock: {e}', 'danger')
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_inventory'))

@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Nested query: Customers with no price alerts
    cursor.execute("""
        SELECT customer_id, first_name, last_name, email
        FROM Customer
        WHERE customer_id NOT IN (
            SELECT DISTINCT customer_id 
            FROM PriceAlert
        )
    """)
    customers_no_alerts = cursor.fetchall()
    
    # Category performance
    cursor.execute("""
        SELECT c.category_name,
               COUNT(DISTINCT p.product_id) as total_products,
               
               COALESCE(AVG(i.price_in_store), 0) as avg_price,
               COALESCE(AVG(i.discount), 0) as avg_discount
               
        FROM Category c
        LEFT JOIN Product p ON c.category_id = p.category_id
        LEFT JOIN Inventory i ON p.product_id = i.product_id
        GROUP BY c.category_id, c.category_name
        HAVING total_products > 0
    """)
    category_stats = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin_analytics.html', 
                         customers_no_alerts=customers_no_alerts,
                         category_stats=category_stats)

@app.route('/admin/products')
@admin_required
def admin_products():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT p.*, c.category_name
        FROM Product p
        JOIN Category c ON p.category_id = c.category_id
        ORDER BY p.product_id
    """)
    products = cursor.fetchall()
    
    cursor.execute("SELECT * FROM Category")
    categories = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin_products.html', products=products, categories=categories)

@app.route('/admin/add_product', methods=['POST'])
@admin_required
def admin_add_product():
    product_name = request.form.get('product_name')
    description = request.form.get('description')
    brand = request.form.get('brand')
    category_id = request.form.get('category_id')
    store_id = request.form.get('store_id')
    quantity = request.form.get('quantity')
    price = request.form.get('price')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Call AddNewProduct procedure
        cursor.callproc('AddNewProduct', 
                       [product_name, description, brand, category_id, store_id, quantity, price])
        
        conn.commit()
        flash('Product added using stored procedure!', 'success')
    except Error as e:
        flash(f'Error adding product: {e}', 'danger')
        
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_products'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)