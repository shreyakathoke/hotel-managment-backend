from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from config import Config
import bcrypt
import os
from flask import send_from_directory
import os
import time
from flask_mail import Mail, Message
from datetime import datetime

import cloudinary
import cloudinary.uploader






app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:5173",
            "https://hotel-managment-website.vercel.app"
        ]
    }
})
@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "https://hotel-managment-website.vercel.app"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return response

# MongoDB connection
client = MongoClient(Config.MONGO_URI)
db = client.get_database()   
users = db["users"]

contacts = db["contacts"]

# ================= SIGNUP =================
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not name or not email or len(password) < 6:
        return jsonify({"error": "Invalid data"}), 400

    if users.find_one({"email": email}):
        return jsonify({"error": "User already exists"}), 400

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    users.insert_one({
        "name": name,
        "email": email,
        "password": hashed
    })

    return jsonify({"message": "Signup successful"}), 201


# ================= LOGIN =================
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    user = users.find_one({"email": email})

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({
        "message": "Login success",
        "user": {
            "name": user["name"],
            "email": user["email"]
        },
        "token": "demo-token"  # frontend needs this
    })



# ================= PROFILE SAVE =================
@app.route("/profile", methods=["POST"])
def save_profile():
    data = request.get_json() or {}

    email = data.get("email")

    if not email:
        return jsonify({"error": "Email required"}), 400

    profile_data = {
        "phone": data.get("phone"),
        "address": data.get("address"),
        "idType": data.get("idType"),
        "idNumber": data.get("idNumber"),
        "photoUrl": data.get("photoUrl"),
    }

    # Update user profile
    users.update_one(
        {"email": email},
        {"$set": profile_data}
    )

    return jsonify({"message": "Profile saved successfully"})



# ================= GET PROFILE =================
@app.route("/profile/<email>", methods=["GET"])
def get_profile(email):
    user = users.find_one({"email": email}, {"_id": 0, "password": 0})

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user)

#=========Delete User =========

@app.route("/users/<email>", methods=["DELETE"])
def delete_user(email):
    result = users.delete_one({"email": email})

    if result.deleted_count == 0:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"message": "User deleted successfully"})

# ================= CREATE BOOKING =================
@app.route("/booking", methods=["POST"])
def create_booking():
    try:
        data = request.get_json(force=True) or {}

        email = data.get("userEmail")
        roomId = data.get("roomId")
        checkIn = data.get("checkInDate")
        checkOut = data.get("checkOutDate")

        if not email or not roomId or not checkIn or not checkOut:
            return jsonify({"error": "Missing required fields"}), 400

        booking_id = "BK-" + str(int(time.time() * 1000))

        booking = {
            "bookingId": booking_id,
            "userEmail": email,
            "roomId": roomId,
            "checkInDate": checkIn,
            "checkOutDate": checkOut,
            "status": "CONFIRMED"
        }

        result = db["bookings"].insert_one(booking)

        # ✅ Convert MongoDB ObjectId to string
        booking["_id"] = str(result.inserted_id)

        return jsonify(booking), 201  # Return the booking object

    except Exception as e:
        return jsonify({"error": "Failed to create booking", "details": str(e)}), 500

# ================= GET BOOKINGS BY USER EMAIL =================
# GET ALL BOOKINGS
@app.route("/booking", methods=["GET"])
def get_all_bookings():
    try:
        bookings = list(db["bookings"].find({}, {"_id": 0}))  # remove MongoDB _id
        return jsonify(bookings), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch bookings", "details": str(e)}), 500

# ================= CANCEL BOOKING =================
@app.route("/booking/cancel", methods=["PUT"])
def cancel_booking():
    try:
        data = request.get_json(force=True) or {}
        booking_id = data.get("bookingId")

        if not booking_id:
            return jsonify({"error": "Booking ID required"}), 400

        result = db["bookings"].update_one(
            {"bookingId": booking_id},
            {"$set": {"status": "CANCELLED"}}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Booking not found"}), 404

        return jsonify({"message": "Booking cancelled"}), 200

    except Exception as e:
        return jsonify({"error": "Failed to cancel booking", "details": str(e)}), 500


#image upload
UPLOAD_FOLDER = "uploads"

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ================= CLOUDINARY CONFIG =================
cloudinary.config(
    cloud_name="YOUR_CLOUD_NAME",
    api_key="YOUR_API_KEY",
    api_secret="YOUR_API_SECRET"
)

@app.route("/rooms", methods=["POST"])
def add_room():
    try:
        # Determine if request is JSON or form-data
        if request.is_json:
            data = request.get_json()
            roomNumber = data.get("roomNumber")
            type_ = data.get("type")
            price = data.get("pricePerNight")
            capacity = data.get("capacity")
            description = data.get("description")
            image_url = data.get("imageUrl", "")
        else:
            roomNumber = request.form.get("roomNumber")
            type_ = request.form.get("type")
            price = request.form.get("pricePerNight")
            capacity = request.form.get("capacity")
            description = request.form.get("description")
            file = request.files.get("image")
            image_url = ""
            if file:
                result = cloudinary.uploader.upload(file)
                image_url = result.get("secure_url", "")

        # Validate required fields
        if not roomNumber or not type_ or not price or not capacity:
            return jsonify({"error": "roomNumber, type, pricePerNight, and capacity are required"}), 400

        # Convert price and capacity to integers safely
        try:
            price = int(price)
            capacity = int(capacity)
        except ValueError:
            return jsonify({"error": "pricePerNight and capacity must be numbers"}), 400

        # Create room object
        room = {
            "roomId": "R-" + str(int(time.time() * 1000)),
            "roomNumber": roomNumber,
            "type": type_,
            "pricePerNight": price,
            "capacity": capacity,
            "available": True,
            "description": description,
            "imageUrl": image_url
        }

        # Insert into DB
        result = db["rooms"].insert_one(room)
        room["_id"] = str(result.inserted_id)

        return jsonify({"message": "Room added successfully", "room": room}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================= GET ALL ROOMS =================
@app.route("/rooms", methods=["GET"])
def get_rooms():
    rooms = list(db["rooms"].find({}, {"_id": 0}))
    return jsonify(rooms)


# ================= GET SINGLE ROOM =================
@app.route("/rooms/<room_id>", methods=["GET"])
def get_room(room_id):
    room = db["rooms"].find_one({"roomId": room_id}, {"_id": 0})

    if not room:
        return jsonify({"error": "Room not found"}), 404

    return jsonify(room)


# ================= UPDATE ROOM =================
@app.route("/rooms/<room_id>", methods=["PUT"])
def update_room(room_id):
    data = request.get_json() or {}

    db["rooms"].update_one(
        {"roomId": room_id},
        {"$set": data}
    )

    return jsonify({"message": "Room updated"})


# ================= DELETE ROOM =================
@app.route("/rooms/<room_id>", methods=["DELETE"])
def delete_room(room_id):
    db["rooms"].delete_one({"roomId": room_id})
    return jsonify({"message": "Room deleted"})



#==============Create Payment=============

@app.route("/payments", methods=["POST"])
def create_payment():
    data = request.get_json() or {}

    payment = {
        "paymentId": "PAY-" + str(int(__import__("time").time() * 1000)),
        "bookingId": data.get("bookingId"),
        "method": data.get("method"),
        "transactionId": data.get("transactionId"),
        "amount": data.get("amount", 5000),
        "status": "SUCCESS",
        "paidAt": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    result = db["payments"].insert_one(payment)

    # ✅ FIX: convert ObjectId to string
    payment["_id"] = str(result.inserted_id)

    return jsonify({
        "message": "Payment successful",
        "payment": payment
    }), 201




#==============GET PAYMENT BY BOOKING ID=============
@app.route("/payments/<booking_id>", methods=["GET"])
def get_payment(booking_id):
    payment = db["payments"].find_one(
        {"bookingId": booking_id},
        {"_id": 0}   # ✅ IMPORTANT
    )

    if not payment:
        return jsonify({"error": "Payment not found"}), 404

    return jsonify(payment)


#==============CANCEL PAYMENT=============
@app.route("/payments/<payment_id>", methods=["PUT"])
def cancel_payment(payment_id):
    db["payments"].update_one(
        {"paymentId": payment_id},
        {"$set": {"status": "CANCELLED"}}
    )

    return jsonify({"message": "Payment cancelled"})

from datetime import datetime


#==============Create Contact =============

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'shreyakathoke01@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-app-password'

mail = Mail(app)


@app.route("/contacts", methods=["POST"])
def create_contact():
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    subject = data.get("subject")
    message = data.get("message")

    if not name or not email or not subject or not message:
        return jsonify({"error": "All required fields missing"}), 400

    # Save to DB
    new_contact = {
        "name": name,
        "email": email,
        "phone": phone,
        "subject": subject,
        "message": message,
        "createdAt": datetime.utcnow()
    }

    result = contacts.insert_one(new_contact)
    new_contact["_id"] = str(result.inserted_id)

    # ✅ SEND EMAIL TO YOU
    try:
        msg = Message(
            subject=f"New Contact: {subject}",
            sender=app.config['MAIL_USERNAME'],
            recipients=["support@eliteresort.com"],
            body=f"""
Name: {name}
Email: {email}
Phone: {phone}

Message:
{message}
            """
        )
        mail.send(msg)

        # ✅ SEND CONFIRMATION TO USER (optional)
        reply = Message(
            subject="We received your message",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email],
            body=f"Hi {name},\n\nWe received your message. We will contact you soon."
        )
        mail.send(reply)

    except Exception as e:
        print("Email Error:", e)

    return jsonify({
        "message": "Message sent successfully ✅",
        "contact": new_contact
    }), 201


#==============GET ALL CONTACTS=============
@app.route("/contacts", methods=["GET"])
def get_contacts():
    all_contacts = list(contacts.find())

    result = []
    for c in all_contacts:
        c["_id"] = str(c["_id"])  # ✅ FIX ObjectId
        result.append(c)

    return jsonify(result)

#==============GET CONTACT BY ID =============
from bson import ObjectId

@app.route("/contacts/<id>", methods=["GET"])
def get_contact_by_id(id):
    contact = contacts.find_one({"_id": ObjectId(id)})

    if not contact:
        return jsonify({"error": "Contact not found"}), 404

    contact["_id"] = str(contact["_id"])  # ✅ FIX
    return jsonify(contact)

#==============DELETE CONTACT=============
@app.route("/contacts/<id>", methods=["DELETE"])
def delete_contact(id):
    result = contacts.delete_one({"_id": ObjectId(id)})

    if result.deleted_count == 0:
        return jsonify({"error": "Contact not found"}), 404

    return jsonify({"message": "Deleted successfully"})


#====admin=======



admins = db["admins"]

def create_default_admin():
    email = "admin@eliteresort.com"
    password = "admin123"

    if not admins.find_one({"email": email}):
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        admins.insert_one({
            "email": email,
            "password": hashed
        })

        print("✅ Default Admin Created")
        print("Email:", email)
        print("Password:", password)


#==========Admin Login===========
@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    admin = admins.find_one({"email": email})

    if not admin:
        return jsonify({"error": "Invalid email or password"}), 401

    if not bcrypt.checkpw(password.encode("utf-8"), admin["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify({
        "message": "Login successful",
        "token": "admin-token-demo",  # later JWT
        "admin": {
            "email": admin["email"]
        }
    })


create_default_admin()

@app.route("/")
def home():
    return "Backend running 🚀"




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Railway's dynamic port, fallback 5000 locally
    app.run(host="0.0.0.0", port=port)