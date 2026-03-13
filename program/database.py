import sqlite3
import os

# File Path
# BASE_DIR = Finds its own location on the device
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH = Looks one directiory up to find the data folder, holding carpentry.db
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "carpentry.db"))

def connect_db():
    """makes the data folder if needed and connects to the db"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def setup_tables():
    """runs on startup, creates tables if they dont exist"""
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

# Job & Priority Logic

def reorder_priorities():
    """fixes IDs after a deletion so there are no gaps"""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM jobs ORDER BY id ASC")
    rows = cursor.fetchall()
    
    # just reassigns each ID in order from 1
    for index, (old_id,) in enumerate(rows, start=1):
        cursor.execute("UPDATE jobs SET id = ? WHERE id = ?", (index, old_id))
    
    connection.commit()
    connection.close()

def change_priority(old_priority, new_priority):
    """handles the move up/down buttons"""
    connection = connect_db()
    cursor = connection.cursor()
    
    # clamp new priority so it cant go out of range
    cursor.execute("SELECT MAX(id) FROM jobs")
    max_priority_row = cursor.fetchone()
    max_priority = max_priority_row[0] if max_priority_row and max_priority_row[0] else 1
    new_priority = max(1, min(new_priority, max_priority))

    if old_priority == new_priority:
        connection.close()
        return

    # use 0 as a temp ID to avoid a conflict
    cursor.execute("UPDATE jobs SET id = 0 WHERE id = ?", (old_priority,))

    # shift everything else to fill the gap
    if old_priority > new_priority:
        cursor.execute("UPDATE jobs SET id = id + 1 WHERE id >= ? AND id < ?", (new_priority, old_priority))
    else:
        cursor.execute("UPDATE jobs SET id = id - 1 WHERE id > ? AND id <= ?", (old_priority, new_priority))

    # put the job back at the right ID
    cursor.execute("UPDATE jobs SET id = ? WHERE id = 0", (new_priority,))
    connection.commit()
    connection.close()

def add_job(customer_name, description, status="Active"):
    """adds a new job to the bottom of the list"""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT MAX(id) FROM jobs")
    max_id_row = cursor.fetchone()
    max_id = max_id_row[0] if max_id_row and max_id_row[0] else 0
    
    # .title() so names are capitalised properly
    cursor.execute("INSERT INTO jobs (id, customer_name, description, status) VALUES (?, ?, ?, ?)", 
                   (max_id + 1, customer_name.title(), description, status))
    connection.commit()
    connection.close()

def get_all_jobs():
    """gets all jobs ordered by priority"""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY id ASC")
    data = cursor.fetchall()
    connection.close()
    return data

def delete_job(job_id):
    """deletes a job then reorders so IDs dont have gaps"""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    connection.commit()
    connection.close()
    reorder_priorities()

# Customer Function

def add_customer(name, phone, email):
    """adds a new customer, or updates them if the name already exists"""
    connection = connect_db()
    cursor = connection.cursor()
    # check if they're already in there
    cursor.execute("SELECT id FROM customers WHERE name = ?", (name.title(),))
    res = cursor.fetchone()
    
    if res:
        # update their details
        cursor.execute("UPDATE customers SET phone = ?, email = ? WHERE id = ?", (phone, email, res[0]))
    else:
        # NULL lets sqlite handle the autoincrement
        cursor.execute("INSERT INTO customers (id, name, phone, email) VALUES (NULL, ?, ?, ?)", (name.title(), phone, email))
    
    connection.commit()
    connection.close()

def get_customers():
    """returns all customers"""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id, name, phone, email FROM customers")
    data = cursor.fetchall()
    connection.close()
    return data

def delete_customer(name):
    """deletes by name since thats what the frontend uses"""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM customers WHERE name = ?", (name,))
    connection.commit()
    connection.close()

# Inventory & Registry Function

def add_to_registry(name):
    """adds a material to the allowed list"""
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
    """adds stock, creates the entry if it doesnt exist yet"""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT quantity FROM inventory WHERE material = ?", (material,))
    result = cursor.fetchone()
    
    if result:
        # add to existing amount
        cursor.execute("UPDATE inventory SET quantity = ? WHERE material = ?", (result[0] + quantity, material))
    else:
        # new material
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
    """takes stock away, returns False if theres not enough"""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT quantity FROM inventory WHERE material = ?", (material,))
    result = cursor.fetchone()
    
    # dont let it go negative
    if result and result[0] >= quantity:
        cursor.execute("UPDATE inventory SET quantity = ? WHERE material = ?", (result[0] - quantity, material))
        connection.commit()
        connection.close()
        return True # worked fine
    
    connection.close()
    return False # not enough stock

def delete_material(name):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM inventory WHERE material = ?", (name,))
    connection.commit()
    connection.close()

def update_job_status(job_id, new_status):
    """updates the status column for a job"""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (new_status, job_id))
    connection.commit()
    connection.close()