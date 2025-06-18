# monitoring.py

import schedule
import time
from datetime import datetime, timedelta
import mysql.connector

# --- Configuration ---
# !!! IMPORTANT: Replace with your MySQL credentials
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "Qwerty@55" 
DB_NAME = "emergency_system1"

def check_missed_checkins():
    """
    Checks for users who haven't checked in recently,
    prints a mock alert, and logs a 'Missed' status.
    """
    print(f"[{datetime.now()}] Running missed check-in job...")
    
    try:
        db = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
        )
        cursor = db.cursor()
        
        # Get all users who should be checking in (e.g., all 'student' roles)
        cursor.execute("SELECT id, username FROM users WHERE role = 'student'")
        users = cursor.fetchall()

        for user_id, username in users:
            # Find the timestamp of the most recent check-in for the user
            cursor.execute(
                "SELECT timestamp FROM checkins WHERE user_id = %s ORDER BY timestamp DESC LIMIT 1",
                (user_id,)
            )
            last_checkin_record = cursor.fetchone()
            
            # Define the time window for a missed check-in
            missed_checkin_threshold = datetime.now() - timedelta(minutes=35)

            # Check if the user has never checked in or if the last check-in is too old
            if not last_checkin_record or last_checkin_record[0] < missed_checkin_threshold:
                # Check if the last recorded status was already 'Missed' to avoid duplicate alerts
                cursor.execute(
                    "SELECT status FROM checkins WHERE user_id = %s ORDER BY timestamp DESC LIMIT 1",
                    (user_id,)
                )
                last_status_record = cursor.fetchone()
                if last_status_record and last_status_record[0] == 'Missed':
                    print(f"User {username} (ID: {user_id}) is still in a 'Missed' state. No new alert logged.")
                    continue

                # --- Trigger an alert and log the missed check-in ---
                print(f"!!! MOCK ALERT: User '{username}' (ID: {user_id}) has missed their scheduled check-in.")
                
                cursor.execute(
                    "INSERT INTO checkins (user_id, timestamp, status) VALUES (%s, %s, %s)",
                    (user_id, datetime.now(), "Missed")
                )
                db.commit()

        cursor.close()
        db.close()

    except mysql.connector.Error as err:
        print(f"Database error during monitoring: {err}")

# --- Schedule the Job ---
# For testing, you can set it to run more frequently, e.g., schedule.every(1).minutes
schedule.every(5).minutes.do(check_missed_checkins)

print("--- Check-In Monitoring Service Started ---")
print("The script will check for missed check-ins every 5 minute.")

# --- Run the Scheduler Loop ---
while True:
    schedule.run_pending()
    time.sleep(60) # Sleep for 60 seconds to avoid high CPU usage