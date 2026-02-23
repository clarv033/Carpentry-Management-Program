import sqlite3
import os

# -File Path-
# BASE_DIR = Finds its own location on the device
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH = Looks one directiory up to find the data folder, holding carpentry.db
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "carpentry.db"))

def connect_db():
    """
    Creates the data folder if it doesn't exist and opens a connection to the database.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def setup_tables():
    """
    Runs when the app starts. It makes sure the tables exist.
    """
    connection = connect_db()
    cursor = connection.cursor()
    
    # Inventory: Stores the materials that are in stock
    cursor.execute("CREATE TABLE IF NOT EXISTS inventory (material TEXT PRIMARY KEY, quantity INTEGER)")
    
    # Registry: A list of allowed materials (prevents typos in the inventory)
    cursor.execute("CREATE TABLE IF NOT EXISTS registry (material_name TEXT PRIMARY KEY)")
    
    # Customers: Basic contact list
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, 
            phone TEXT, 
            email TEXT
        )
    """)
    
    # Jobs: The main tracker. The ID (PK) acts as a priority number too
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            customer_name TEXT,
            description TEXT,
            status TEXT
        )
    """)
    connection.commit()
    connection.close()

# -Job & Priority Logic-

def reorder_priorities():
    """
    This function loops through to make sure it doesnt skip IDs 
    (if you delete a job, it will start from x again, where x is the lowest number possible)
    """
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM jobs ORDER BY id ASC")
    rows = cursor.fetchall()
    
    # Re-assigns IDs based on their current sorted order
    for index, (old_id,) in enumerate(rows, start=1):
        cursor.execute("UPDATE jobs SET id = ? WHERE id = ?", (index, old_id))
    
    connection.commit()
    connection.close()

def change_priority(old_priority, new_priority):
    """
    This handles the Move Up and Move Down buttons which manages priority.
    """
    connection = connect_db()
    cursor = connection.cursor()
    
    # Make sure the new priority isn't higher than the total number of jobs
    cursor.execute("SELECT MAX(id) FROM jobs")
    max_priority_row = cursor.fetchone()
    max_priority = max_priority_row[0] if max_priority_row and max_priority_row[0] else 1
    new_priority = max(1, min(new_priority, max_priority))

    if old_priority == new_priority:
        connection.close()
        return

    # Temporary ID 0 is used so we dont have two jobs with the same ID
    cursor.execute("UPDATE jobs SET id = 0 WHERE id = ?", (old_priority,))

    # Shift other jobs up or down to fill the gap
    if old_priority > new_priority:
        cursor.execute("UPDATE jobs SET id = id + 1 WHERE id >= ? AND id < ?", (new_priority, old_priority))
    else:
        cursor.execute("UPDATE jobs SET id = id - 1 WHERE id > ? AND id <= ?", (old_priority, new_priority))

    # Move the original job from ID 0 to the new priority ID
    cursor.execute("UPDATE jobs SET id = ? WHERE id = 0", (new_priority,))
    connection.commit()
    connection.close()

def add_job(customer_name, description, status="Active"):
    """Adds a new job to the end of the list."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT MAX(id) FROM jobs")
    max_id_row = cursor.fetchone()
    max_id = max_id_row[0] if max_id_row and max_id_row[0] else 0
    
    # Uses .title() to make sure names look neat (stuff like "joHn" becomes "John")
    cursor.execute("INSERT INTO jobs (id, customer_name, description, status) VALUES (?, ?, ?, ?)", 
                   (max_id + 1, customer_name.title(), description, status))
    connection.commit()
    connection.close()

def get_all_jobs():
    """Fetches every job from the database, sorted by their priority (ID)."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY id ASC")
    data = cursor.fetchall()
    connection.close()
    return data

def delete_job(job_id):
    """Deletes a job and then starts the re-order function to fix the IDs."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    connection.commit()
    connection.close()
    reorder_priorities()

# -Customer Function-

def add_customer(name, phone, email):
    """Adds a customer or updates their info if the name already exists."""
    connection = connect_db()
    cursor = connection.cursor()
    # Check if they exist first by name
    cursor.execute("SELECT id FROM customers WHERE name = ?", (name.title(),))
    res = cursor.fetchone()
    
    if res:
        # If they exist, update existing record
        cursor.execute("UPDATE customers SET phone = ?, email = ? WHERE id = ?", (phone, email, res[0]))
    else:
        # If new, let SQLite handle the ID (NULL triggers AUTOINCREMENT)
        cursor.execute("INSERT INTO customers (id, name, phone, email) VALUES (NULL, ?, ?, ?)", (name.title(), phone, email))
    
    connection.commit()
    connection.close()

def get_customers():
    """Fetches customers with IDs."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id, name, phone, email FROM customers")
    data = cursor.fetchall()
    connection.close()
    return data

def delete_customer(name):
    """Deletes by name to match frontend logic."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM customers WHERE name = ?", (name,))
    connection.commit()
    connection.close()

# -Inventory & Registry Function-

def add_to_registry(name):
    """Adds a material to the list of allowed items."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("INSERT OR IGNORE INTO registry VALUES (?)", (name.title(),))
    connection.commit()
    connection.close()

def remove_from_registry(name):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM registry WHERE material_name = ?", (name,))
    connection.commit()
    connection.close()

def get_registry():
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT material_name FROM registry ORDER BY material_name ASC")
    # Converts list of tuples into a list of strings
    data = [row[0] for row in cursor.fetchall()]
    connection.close()
    return data

def add_inventory(material, quantity):
    """Updates stock levels, if the item isn't in stock it creates a new entry."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT quantity FROM inventory WHERE material = ?", (material,))
    result = cursor.fetchone()
    
    if result:
        # If material exists, add the new amount to the old amount
        cursor.execute("UPDATE inventory SET quantity = ? WHERE material = ?", (result[0] + quantity, material))
    else:
        # If not, create it from scratch
        cursor.execute("INSERT INTO inventory VALUES (?, ?)", (material, quantity))
    
    connection.commit()
    connection.close()

def get_inventory():
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM inventory")
    data = cursor.fetchall()
    connection.close()
    return data

def use_inventory(material, quantity):
    """Reduces stock, It checks first to make sure you have enough before subtracting."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT quantity FROM inventory WHERE material = ?", (material,))
    result = cursor.fetchone()
    
    # Logic check to prevent negative stock
    if result and result[0] >= quantity:
        cursor.execute("UPDATE inventory SET quantity = ? WHERE material = ?", (result[0] - quantity, material))
        connection.commit()
        connection.close()
        return True # Tells the app it was successful
    
    connection.close()
    return False # Tells the app there wasn't enough stock

def delete_material(name):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM inventory WHERE material = ?", (name,))
    connection.commit()
    connection.close()

def update_job_status(job_id, new_status):
    """Updates the 'Status' column (e.g., 'Finished', 'Pending') for a job."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (new_status, job_id))
    connection.commit()
    connection.close()