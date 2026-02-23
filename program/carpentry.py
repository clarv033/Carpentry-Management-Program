# -Libaries-
import sys  # System parameters and functions
import csv  # Read/write inventory report file
import os   # Handles the file paths so it works on any operating system

# -PyQt6 UI Framework-
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, 
    QVBoxLayout, QPushButton, QStackedWidget, QLabel, 
    QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem, 
    QHeaderView, QCompleter, QFrame
)
from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtGui import QColor

# -Local Modules-
import database  # This connects carpentry.py to database.py

# -Main program class (GUI)-
class CarpentryApp(QMainWindow):
    """
    The CarpentryApp class is what makes the UI and handles the user interactions
    """
    def __init__(self):
        super().__init__()
        
        # Initialised the SQLIte database structure when the program begins
        database.setup_tables()
        
        # Window Config
        self.setWindowTitle("Carpentry Management System")
        self.setMinimumSize(1150, 500) 

        # Initialisation Sequence
        self.setup_ui()             # Make the layout
        self.load_inventory_data()  # Load the inventory data from carpentry.db
        self.load_customer_data() # Load the customer data from carpentry.db
        self.load_job_data() # Load the job data from carpentry.db
        self.update_completers()    # Initialise the search bar's autocomplete features

    def setup_ui(self):
        """
        Organises the layout into the sidebar (left side) and the main content (which is on the right)
        """
        container = QWidget()
        layout = QHBoxLayout(container) # Horizontal layout: [Sidebar] | [Main Content]
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -Sidebar Creation-
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setStyleSheet("background-color: #2b2b2b; border-right: 1px solid #333;")
        self.sidebar = QVBoxLayout(self.sidebar_widget) # The buttons are vertically stacked on the sidebar
        self.sidebar.setContentsMargins(15, 20, 15, 20)
        self.sidebar.setSpacing(10)

        # -Navgiation Buttons-
        self.btn_jobs = QPushButton("Jobs")        
        self.btn_customers = QPushButton("Customers") 
        self.btn_inventory = QPushButton("Inventory") 
        
        # -Button Styling-
        button_style = "padding: 10px; text-align: left; font-weight: bold;"
        for btn in [self.btn_jobs, self.btn_customers, self.btn_inventory]:
            btn.setStyleSheet(button_style)
            self.sidebar.addWidget(btn)
        
        self.sidebar.addStretch() # This pushes the buttons to the top, leaving space for future buttons below

        # -Divider Line-
        self.line_separator = QFrame()
        self.line_separator.setFrameShape(QFrame.Shape.VLine)
        self.line_separator.setStyleSheet("color: #444; width: 2px;") 

        # -Main Content Area-
        self.pages = QStackedWidget() # This holds the 3 pages that occur when you click the buttons
        self.pages.setContentsMargins(20, 10, 20, 10)
        self.setup_pages() # Builds the individual pages

        # -Connect button clicks to main content page-
        self.btn_jobs.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        self.btn_customers.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        self.btn_inventory.clicked.connect(lambda: self.pages.setCurrentIndex(2))

        # -Add components to horizontal layout-
        layout.addWidget(self.sidebar_widget, 1)
        layout.addWidget(self.line_separator)
        layout.addWidget(self.pages, 5) # Main content gets more space than sidebar
        
        self.setCentralWidget(container)

    def setup_pages(self):
        """
        Constructs the Jobs, Customers, and Inventory views.
        """
        # -Job Page-
        self.jobs_page = QWidget()
        jobs_layout = QVBoxLayout(self.jobs_page)
        jobs_layout.addWidget(QLabel("<h2>Job Tracker</h2>"))

        # Search Bar for Jobs
        self.job_search = QLineEdit()
        self.job_search.setPlaceholderText("🔍 Filter jobs by customer...")
        self.job_search.textChanged.connect(self.load_job_data)
        
        # Completer provides the suggestions based on names in the database
        self.job_search_completer = QCompleter()
        self.job_search_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.job_search.setCompleter(self.job_search_completer)
        jobs_layout.addWidget(self.job_search)

        # Inputs for adding a New Job
        job_input_layout = QHBoxLayout()
        self.job_cust_input = QLineEdit(); self.job_cust_input.setPlaceholderText("Customer Name")
        self.job_desc_input = QLineEdit(); self.job_desc_input.setPlaceholderText("Job Description")
        self.job_status_input = QLineEdit(); self.job_status_input.setPlaceholderText("Status")

        job_input_layout.addWidget(self.job_cust_input, 2)
        job_input_layout.addWidget(self.job_desc_input, 3)
        job_input_layout.addWidget(self.job_status_input, 1)
        jobs_layout.addLayout(job_input_layout)

        # Job Control Buttons (Add, Priority, Delete)
        job_btn_layout = QHBoxLayout()
        btn_add_job = QPushButton("Add Job"); btn_add_job.clicked.connect(self.save_job)
        btn_upd_job = QPushButton("Update Status"); btn_upd_job.clicked.connect(self.update_job_status)
        
        # Lambda lets us pass arguments through a click
        btn_up = QPushButton("▲ Move Up"); btn_up.clicked.connect(lambda: self.move_priority(-1))
        btn_down = QPushButton("▼ Move Down"); btn_down.clicked.connect(lambda: self.move_priority(1))
        
        btn_del_job = QPushButton("Delete Job"); btn_del_job.clicked.connect(self.delete_job)
        btn_del_job.setStyleSheet("background-color: #442222; color: white;")
        
        job_btn_layout.addWidget(btn_add_job)
        job_btn_layout.addWidget(btn_upd_job)
        job_btn_layout.addWidget(btn_up)
        job_btn_layout.addWidget(btn_down)
        job_btn_layout.addWidget(btn_del_job)
        jobs_layout.addLayout(job_btn_layout)

        # The Table for displaying Jobs
        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(4)
        self.jobs_table.setHorizontalHeaderLabels(["Priority", "Customer", "Description", "Status"])
        self.jobs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        jobs_layout.addWidget(self.jobs_table)
        self.pages.addWidget(self.jobs_page)

        # -Customer Page-
        self.customer_page = QWidget()
        cust_layout = QVBoxLayout(self.customer_page)
        cust_layout.addWidget(QLabel("<h2>Customer Database</h2>"))
        self.cust_search = QLineEdit(); self.cust_search.setPlaceholderText("🔍 Search Customers...")
        self.cust_search.textChanged.connect(self.load_customer_data)
        cust_layout.addWidget(self.cust_search)

        c_in = QHBoxLayout()
        self.cust_name_input = QLineEdit(); self.cust_name_input.setPlaceholderText("Full Name")
        self.cust_phone_input = QLineEdit(); self.cust_phone_input.setPlaceholderText("Phone Number")
        self.cust_email_input = QLineEdit(); self.cust_email_input.setPlaceholderText("Email Address")
        c_in.addWidget(self.cust_name_input); c_in.addWidget(self.cust_phone_input); c_in.addWidget(self.cust_email_input)
        cust_layout.addLayout(c_in)

        c_btn = QHBoxLayout()
        btn_sc = QPushButton("Add/Update Customer"); btn_sc.clicked.connect(self.save_customer)
        btn_dc = QPushButton("Delete Customer"); btn_dc.setStyleSheet("background-color: #442222; color: white;"); btn_dc.clicked.connect(self.delete_customer)
        c_btn.addWidget(btn_sc); c_btn.addWidget(btn_dc)
        cust_layout.addLayout(c_btn)

        self.customer_table = QTableWidget(); self.customer_table.setColumnCount(4)
        self.customer_table.setHorizontalHeaderLabels(["ID", "Name", "Phone", "Email"])
        self.customer_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        cust_layout.addWidget(self.customer_table)
        self.pages.addWidget(self.customer_page)

        # -Inventory Page-
        self.inventory_page = QWidget()
        inv_layout = QVBoxLayout(self.inventory_page)
        inv_layout.addWidget(QLabel("<h2>Inventory Management</h2>"))
        
        t_bar = QHBoxLayout()
        self.inv_search = QLineEdit(); self.inv_search.setPlaceholderText("🔍 Search Inventory...")
        self.inv_search.textChanged.connect(self.load_inventory_data)
        btn_exp = QPushButton("Export CSV"); btn_exp.clicked.connect(self.export_to_csv)
        t_bar.addWidget(self.inv_search, 3); t_bar.addWidget(btn_exp, 1)
        inv_layout.addLayout(t_bar)

        r_layout = QHBoxLayout()
        self.reg_input = QLineEdit(); self.reg_input.setPlaceholderText("Add material to database...")
        btn_ar = QPushButton("Add to Database"); btn_ar.clicked.connect(self.add_to_registry_list)
        btn_rr = QPushButton("Remove from database"); btn_rr.clicked.connect(self.remove_from_registry_list)
        r_layout.addWidget(self.reg_input, 2); r_layout.addWidget(btn_ar, 1); r_layout.addWidget(btn_rr, 1)
        inv_layout.addLayout(r_layout)

        i_in = QHBoxLayout()
        self.mat_input = QLineEdit(); self.mat_input.setPlaceholderText("Material Name")
        self.qty_input = QLineEdit(); self.qty_input.setPlaceholderText("Qty")
        i_in.addWidget(self.mat_input, 3); i_in.addWidget(self.qty_input, 1)
        inv_layout.addLayout(i_in)

        i_btn = QHBoxLayout()
        btn_us = QPushButton("Update Stock"); btn_us.clicked.connect(self.save_to_inventory)
        btn_use = QPushButton("Use Stock"); btn_use.clicked.connect(self.remove_stock)
        btn_dm = QPushButton("Delete Stock")
        btn_dm.setStyleSheet("background-color: #442222; color: white;")
        btn_dm.clicked.connect(self.delete_from_inventory)
        
        i_btn.addWidget(btn_us); i_btn.addWidget(btn_use); i_btn.addWidget(btn_dm)
        inv_layout.addLayout(i_btn)

        self.inventory_table = QTableWidget(); self.inventory_table.setColumnCount(2)
        self.inventory_table.setHorizontalHeaderLabels(["Material", "Quantity"])
        self.inventory_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        inv_layout.addWidget(self.inventory_table)
        self.pages.addWidget(self.inventory_page)

    # -Function Logic-

    def update_completers(self):
        """Refreshes the predictive text lists from the database with Case Insensitivity."""
        mats = database.get_registry()
        customers_data = database.get_customers()
        cust_list = [str(customer[1]) for customer in customers_data] 
        
        # Helper to set up completers consistently
        def set_up_comp(widget, data_list):
            comp = QCompleter(data_list)
            comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            widget.setCompleter(comp)

        set_up_comp(self.mat_input, mats)
        set_up_comp(self.reg_input, mats)
        set_up_comp(self.job_cust_input, cust_list)
        
        # This allows the customer search bar to autocomplete
        set_up_comp(self.cust_search, cust_list)
        self.job_search_completer.setModel(QStringListModel(cust_list))

    def move_priority(self, direction):
        """Handles moving a job up or down in the list."""
        row = self.jobs_table.currentRow()
        if row >= 0: # This ensures a row is selected before moving it
            current_p = int(self.jobs_table.item(row, 0).text())
            new_p = current_p + direction
            database.change_priority(current_p, new_p)
            self.load_job_data()
            
            # This re-selects the row at the new position
            target_row = max(0, min(row + direction, self.jobs_table.rowCount() - 1))
            self.jobs_table.selectRow(target_row)

    def save_job(self):
        """Grabs data from inputs and sends it to the database."""
        customer = self.job_cust_input.text().strip()
        description = self.job_desc_input.text().strip()
        status = self.job_status_input.text().strip() or "Active" # Default status if empty
        
        if customer and description: # This prevents empty entries
            database.add_job(customer, description, status)
            self.load_job_data()
            self.job_cust_input.clear()
            self.job_desc_input.clear()

    def load_job_data(self):
        """Clears the table and re-populates it based on database records."""
        self.jobs_table.setRowCount(0)
        search = self.job_search.text().lower()
        
        # Loops through every job returned from the database
        for row in database.get_all_jobs():
            if search in str(row[1]).lower():
                idx = self.jobs_table.rowCount()
                self.jobs_table.insertRow(idx)
                # Nested loop to fill the cells of the row
                for i in range(4): 
                    self.jobs_table.setItem(idx, i, QTableWidgetItem(str(row[i])))

    def update_job_status(self):
        """Updates the status of a specific job ID."""
        row = self.jobs_table.currentRow()
        ns = self.job_status_input.text().strip()
        if row >= 0 and ns:
            job_id = self.jobs_table.item(row, 0).text()
            database.update_job_status(job_id, ns)
            self.load_job_data()

    def delete_job(self):
        """Removes a job and triggers the ID re-ordering in the database."""
        row = self.jobs_table.currentRow()
        if row >= 0:
            database.delete_job(self.jobs_table.item(row, 0).text())
            self.load_job_data()

    def save_customer(self):
        """Saves a new customer or updates an existing one with data validation."""
        name = self.cust_name_input.text().strip()
        phone = self.cust_phone_input.text().strip()
        email = self.cust_email_input.text().strip()
        
        if name and phone:
            database.add_customer(name, phone, email)
            self.load_customer_data()
            self.update_completers()
            self.cust_name_input.clear()
            self.cust_phone_input.clear()
            self.cust_email_input.clear()
        else:
            QMessageBox.warning(self, "Invalid Data", "Customer Name and Phone Number are required.")

    def load_customer_data(self):
        """Populates the customer table with case-insensitive filtering."""
        self.customer_table.setRowCount(0)
        status_search = self.cust_search.text().lower()
        
        # Converts row items to string
        for row in database.get_customers():
            # row[0]=ID, row[1]=Name, row[2]=Phone, row[3]=Email
            name_text = str(row[1]).lower()
            phone_text = str(row[2]).lower()
            
            # Check if search term is in name or phone
            if status_search in name_text or status_search in phone_text:
                idx = self.customer_table.rowCount()
                self.customer_table.insertRow(idx)
                for i in range(len(row)): 
                    self.customer_table.setItem(idx, i, QTableWidgetItem(str(row[i])))

    def delete_customer(self):
        row = self.customer_table.currentRow()
        if row >= 0:
            customer_name = self.customer_table.item(row, 1).text()
            database.delete_customer(customer_name)
            self.load_customer_data()
            self.update_completers()

    def add_to_registry_list(self):
        """Adds a material name to the allowed 'registry' list."""
        database.add_to_registry(self.reg_input.text())
        self.update_completers()

    def remove_from_registry_list(self):
        """Removes a material name from the allowed 'registry' list."""
        database.remove_from_registry(self.reg_input.text())
        self.update_completers()

    def save_to_inventory(self):
        """Adds stock to a specific material with validation feedback."""
        material = self.mat_input.text().strip()
        quantity = self.qty_input.text().strip()
        
        # Ensures inputs are not empty and quantity is numerical
        if not material or not quantity:
            QMessageBox.warning(self, "Input Error", "Please provide both material and quantity.")
            return

        registered_mats = [m.lower() for m in database.get_registry()]
        if material.lower() in registered_mats and quantity.isdigit():
            # Match the registry's specific casing from the database
            idx = registered_mats.index(material.lower())
            actual_name = database.get_registry()[idx]
            database.add_inventory(actual_name, int(quantity))
            self.load_inventory_data()
            self.mat_input.clear()
            self.qty_input.clear()
        elif not quantity.isdigit():
            QMessageBox.warning(self, "Invalid Quantity", "Please enter a whole number for quantity.")
        else:
            QMessageBox.warning(self, "Unknown Material", "This material is not in the database registry.")

    def load_inventory_data(self):
        """Populates the inventory table."""
        self.inventory_table.setRowCount(0)
        status = self.inv_search.text().lower()
        for row in database.get_inventory():
            if status in row[0].lower():
                idx = self.inventory_table.rowCount()
                self.inventory_table.insertRow(idx)
                self.inventory_table.setItem(idx, 0, QTableWidgetItem(row[0]))
                self.inventory_table.setItem(idx, 1, QTableWidgetItem(str(row[1])))

    def remove_stock(self):
        """Deducts stock from a selected item with insufficient stock feedback."""
        row = self.inventory_table.currentRow()
        quantity_str = self.qty_input.text().strip()
        
        if row >= 0 and quantity_str.isdigit():
            material_name = self.inventory_table.item(row, 0).text()
            quantity_to_use = int(quantity_str)
            
            # Call database to check if use was successful
            success = database.use_inventory(material_name, quantity_to_use)
            
            if success:
                self.load_inventory_data()
                self.qty_input.clear()
            else:
                QMessageBox.warning(self, "Stock Error", f"Insufficient stock for {material_name}.")
        elif row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a material from the table first.")

    def delete_from_inventory(self):
        """Hard-delete of a material row from the stock table."""
        row = self.inventory_table.currentRow()
        if row >= 0:
            database.delete_material(self.inventory_table.item(row, 0).text())
            self.load_inventory_data()

    def export_to_csv(self):
        """Dumps the current inventory table into a readable CSV file for use on spreadsheets."""
        with open("inventory_report.csv", "w", newline="") as f:
            csv.writer(f).writerows(database.get_inventory())

# -Application Creation-
if __name__ == "__main__":
    app = QApplication(sys.argv) # Create the application instance
    window = CarpentryApp()      # Create the main window instance
    window.show()                # Display the window
    sys.exit(app.exec())         # Execute the app loop