# app.py
# Add this import at the top of app.py

# Add these imports at the top of your app.py
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from webrtc_server import handle_offer
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# --- App Initialization ---
app = Flask(__name__)
limiter = Limiter(app=app, key_func=get_remote_address)

# --- Configuration ---
# ... (keep existing DB_HOST, DB_USER, etc. config)

# Configure JWT
# !!! IMPORTANT: Change this to a long, random, secret string in production!
app.config["JWT_SECRET_KEY"] = "a-super-secret-key-that-is-not-this" 
jwt = JWTManager(app)


# ... (keep get_db(), mock notifications, etc.)


# --- API Endpoints ---

# NEW: Add a /login endpoint (this one is public)
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', None)
    password = data.get('password', None)

    # For the prototype, we use a mock password check.
    # In a real app, you would query the database and verify a hashed password.
    if username != 'testuser' or password != 'test':
        return jsonify({"msg": "Bad username or password"}), 401

    # Create a new token with the username as the identity
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token)


# PROTECTED: Add the @jwt_required() decorator to your existing endpoints
@app.route('/alert', methods=['POST'])
@jwt_required() # <-- Add this decorator
@limiter.limit("1 per 5 minutes")
def alert():
    # ... (existing alert code)
    # You can now get the identity of the user who made the request
    current_user = get_jwt_identity()
    print(f"Alert submitted by authenticated user: {current_user}")
    # ... (rest of the alert code)
    # Note: You might want to use current_user instead of the user_id from the JSON body for security
    
@app.route('/checkin', methods=['POST'])
@jwt_required() # <-- Add this decorator
def checkin():
    # ... (existing checkin code)

@app.route('/voip', methods=['POST'])
@jwt_required() # <-- Add this decorator
async def voip():
    """Handles WebRTC signaling to initiate a VoIP call."""
    data = request.json
    user_id = data.get('user_id')
    offer = data.get('offer') # The WebRTC offer from the client app

    if not user_id or not offer:
        return jsonify({"error": "Missing user_id or offer"}), 400

    print(f"--- Mock VoIP Call Initiation ---")
    print(f"Received WebRTC offer for user_id: {user_id}")
    
    # Process the offer and get an answer
    answer = await handle_offer(offer)
    
    print(f"Sending WebRTC answer back to user_id: {user_id}")
    print("---------------------------------")
    
    return jsonify({"answer": answer})

@app.route('/chat', methods=['POST'])
@jwt_required() # <-- Add this decorator
def chat():
    """A fallback text chat endpoint."""
    data = request.json
    user_id = data.get('user_id')
    message = data.get('message')

    if not user_id or not message:
        return jsonify({"error": "Missing user_id or message"}), 400

    print(f"--- Mock Chat Message ---")
    print(f"From User ID {user_id}: {message}")
    print("-------------------------")
    
    return jsonify({"status": "Message received"})

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import mysql.connector
from cryptography.fernet import Fernet
from datetime import datetime

# --- App Initialization ---
app = Flask(__name__)

# --- Configuration ---
# !!! IMPORTANT: Replace with your MySQL credentials
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "Qwerty@55" 
DB_NAME = "emergency_system1"

# Generate an encryption key for this session
# NOTE: In a real app, this key must be securely stored and managed, not regenerated on startup.
key = Fernet.generate_key()
cipher = Fernet(key)

# --- Rate Limiting Setup ---
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# --- Database Helper Function ---
def get_db():
    """Establishes a connection to the database."""
    try:
        db = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return db
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

# --- Mock Notification Functions ---
def mock_notification(user_id, emergency_type, encrypted_location):
    """Simulates sending a push notification by printing to the console."""
    # We can decrypt here because we are using the same 'cipher' instance from this app session
    decrypted_location = cipher.decrypt(encrypted_location).decode()
    print("--- MOCK PUSH NOTIFICATION ---")
    print(f"Alert from User ID: {user_id}")
    print(f"Emergency Type: {emergency_type}")
    print(f"Location: {decrypted_location}")
    print("----------------------------")

def mock_sms(user_id, emergency_type):
    """Simulates sending an SMS by printing to the console."""
    print(f"--- MOCK SMS ---")
    print(f"Emergency: {emergency_type} reported by user {user_id}. Please check the system for details.")
    print("----------------")


# --- API Endpoints ---
@app.route('/')
def index():
    return jsonify({"status": "Backend running"})

@app.route('/alert', methods=['POST'])
@limiter.limit("1 per 5 minutes") # Rate limit this specific endpoint
def alert():
    """Receives an emergency alert, logs it, and triggers mock notifications."""
    data = request.json
    user_id = data.get('user_id')
    emergency_type = data.get('emergency_type')
    location_str = data.get('location')

    if not all([user_id, emergency_type, location_str]):
        return jsonify({"error": "Missing data"}), 400

    # Encrypt the location data
    encrypted_location = cipher.encrypt(location_str.encode())

    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = db.cursor()
    try:
        # Insert the alert into the database
        cursor.execute(
            "INSERT INTO alerts (user_id, emergency_type, location, timestamp) VALUES (%s, %s, %s, %s)",
            (user_id, emergency_type, encrypted_location, datetime.now())
        )
        db.commit()

        # Trigger mock notifications after successful DB insertion
        mock_notification(user_id, emergency_type, encrypted_location)
        mock_sms(user_id, emergency_type)

        return jsonify({
            "status": "Alert received",
            "user_id": user_id,
            "emergency_type": emergency_type
        })

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cursor.close()
        db.close()

# Handle rate limit exceeded error
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded", "message": str(e.description)}), 429

# --- Run the App ---
if __name__ == '__main__':
    # Use debug=False for production
    app.run(debug=True, port=5000)

# Add this new endpoint to your existing app.py file

@app.route('/checkin', methods=['POST'])
def checkin():
    """Logs a user's well-being check-in."""
    data = request.json
    user_id = data.get('user_id')
    status = data.get('status', 'OK') # Default status is 'OK'

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO checkins (user_id, timestamp, status) VALUES (%s, %s, %s)",
            (user_id, datetime.now(), status)
        )
        db.commit()
        return jsonify({"status": "Check-in recorded", "user_id": user_id})
    except mysql.connector.Error as err:
        # Handle cases like a non-existent user_id
        return jsonify({"error": f"Database error: {err}"}), 500
    finally:
        cursor.close()
        db.close()

