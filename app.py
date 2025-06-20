from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import mysql.connector
from cryptography.fernet import Fernet
from datetime import datetime
import asyncio

# --- App Initialization ---
app = Flask(__name__)
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

# --- Configuration ---
# !!! IMPORTANT: Replace with your MySQL credentials
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "Qwerty@55" 
DB_NAME = "emergency_system1"

# Configure JWT
# !!! IMPORTANT: Change this to a long, random, secret string in production!
app.config["JWT_SECRET_KEY"] = "a-super-secret-key-that-is-not-this" 
jwt = JWTManager(app)

# Generate an encryption key for this session
# NOTE: In a real app, this key must be securely stored and managed, not regenerated on startup.
key = Fernet.generate_key()
cipher = Fernet(key)

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

# --- Notification Functions ---
def mock_notification(user_id, emergency_type, encrypted_location):
    """Simulates sending a push notification by printing to the console."""
    # We can decrypt here because we are using the same 'cipher' instance from this app session
    decrypted_location = cipher.decrypt(encrypted_location).decode()
    print("--- PUSH NOTIFICATION ---")
    print(f"Alert from User ID: {user_id}")
    print(f"Emergency Type: {emergency_type}")
    print(f"Location: {decrypted_location}")
    print("----------------------------")

def mock_sms(user_id, emergency_type):
    """Simulates sending an SMS by printing to the console."""
    print(f"--- SMS ---")
    print(f"Emergency: {emergency_type} reported by user {user_id}. Please check the system for details.")
    print("----------------")

# WebRTC handler function 
async def handle_offer(offer):
    """Mock WebRTC offer handler - replace with actual implementation"""
    print(f"Processing WebRTC offer: {offer[:50]}...")
    # Return an answer
    return {"type": "answer", "sdp": "mock_answer_sdp_data"}

# --- API Endpoints ---
@app.route('/')
def index():
    return jsonify({"status": "Backend running"})

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

@app.route('/alert', methods=['POST'])
@jwt_required() # <-- Add this decorator
@limiter.limit("1 per 5 minutes") # Rate limit this specific endpoint
def alert():
    """Receives an emergency alert, logs it, and triggers mock notifications."""
    # You can now get the identity of the user who made the request
    current_user = get_jwt_identity()
    print(f"Alert submitted by authenticated user: {current_user}")
    
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

@app.route('/checkin', methods=['POST'])
@jwt_required() # <-- Add this decorator
def checkin():
    """Logs a user's well-being check-in."""
    current_user = get_jwt_identity()
    print(f"Check-in submitted by authenticated user: {current_user}")
    
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

@app.route('/voip', methods=['POST'])
@jwt_required()  # <-- Add this decorator
def voip():
    """Handles WebRTC signaling to initiate a VoIP call."""
    current_user = get_jwt_identity()
    print(f"VoIP call initiated by authenticated user: {current_user}")
    
    data = request.json
    user_id = data.get('user_id')
    offer = data.get('offer')  # The WebRTC offer from the client app

    if not user_id or not offer:
        return jsonify({"error": "Missing user_id or offer"}), 400

    print(f"--- VoIP Call Initiation ---")
    print(f"Received WebRTC offer for user_id: {user_id}")
    
    # Process the offer and get an answer (using asyncio.run for the async function)
    try:
        answer = asyncio.run(handle_offer(offer))
    except Exception as e:
        print(f"Error processing WebRTC offer: {e}")
        return jsonify({"error": "Failed to process WebRTC offer"}), 500
    
    print(f"Sending WebRTC answer back to user_id: {user_id}")
    print("---------------------------------")
    
    return jsonify({"answer": answer})

@app.route('/chat', methods=['POST'])
@jwt_required() # <-- Add this decorator
def chat():
    """A fallback text chat endpoint."""
    current_user = get_jwt_identity()
    print(f"Chat message from authenticated user: {current_user}")
    
    data = request.json
    user_id = data.get('user_id')
    message = data.get('message')

    if not user_id or not message:
        return jsonify({"error": "Missing user_id or message"}), 400

    print(f"--- Chat Message ---")
    print(f"From User ID {user_id}: {message}")
    print("-------------------------")
    
    return jsonify({"status": "Message received"})

# Handle rate limit exceeded error
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded", "message": str(e.description)}), 429

# --- Run the App ---
if __name__ == '__main__':
    # Use debug=False for production
    app.run(debug=True, port=5000)

