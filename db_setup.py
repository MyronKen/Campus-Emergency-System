import mysql.connector
from cryptography.fernet import Fernet

# --- Database Connection ---
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "Qwerty@55" 
DB_NAME = "emergency_system1"

# --- Generate an encryption key ---
key = Fernet.generate_key()
print(f"Generated Encryption Key (for testing): {key.decode()}") # Optional: print key for testing
cipher = Fernet(key)

try:
    # --- Connect to the database ---
    db = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = db.cursor()
    print("Successfully connected to the database.")

    # --- SQL Statements to Create Tables ---
    
    # Create 'users' table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            role ENUM('student', 'security') DEFAULT 'student'
        )
    """)
    print("Table 'users' created or already exists.")

    # Create 'alerts' table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            emergency_type ENUM('Medical', 'Security', 'Fire', 'Other'),
            location BLOB,  -- For encrypted location data
            timestamp DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    print("Table 'alerts' created or already exists.")

    # Create 'checkins' table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkins (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            timestamp DATETIME,
            status ENUM('OK', 'Missed'),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    print("Table 'checkins' created or already exists.")

    # --- Commit changes and close connection ---
    db.commit()
    print("Database schema setup complete. Tables have been created.")

except mysql.connector.Error as err:
    print(f"Error: {err}")

finally:
    if 'db' in locals() and db.is_connected():
        cursor.close()
        db.close()
        print("MySQL connection is closed.")
