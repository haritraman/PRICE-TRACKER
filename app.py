import json
from flask import Flask, render_template, request, redirect, session, jsonify
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import atexit
import datetime
import smtplib  
from email.mime.text import MIMEText  
from email.mime.multipart import MIMEMultipart  
 


from flask_mail import Mail, Message
import random
load_dotenv()
app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("EMAIL_USER")  
app.config['MAIL_PASSWORD'] = os.getenv("EMAIL_PASS") 
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("EMAIL_USER")


mail = Mail(app)
otp_store = {}  # Temporary storage for OTPs





app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
users = {}
tracked_products = {}

def save_users():
    with open("users.json", "w") as f:
        json.dump(users, f)

def load_users():
    global users
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
            print("Users loaded:", users)  # Debugging
    except FileNotFoundError:
        users = {}
    except json.JSONDecodeError:
        users = {}  # If file is empty or corrupt, reset users


#load_users()

def send_telegram_message(chat_id, message):
    print(f"Sending Telegram alert to {chat_id}: {message}")  # Debugging
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id": chat_id, "text": message}
    response=requests.post(url, params=params)
    #print("Telegram API response: ",response.json())

def get_price(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        #print(f"Response Status: {response.status_code}")
        #print(f"Response Text: {response.text[:500]}")  # Print first 500 characters for debugging
        soup = BeautifulSoup(response.content, 'html.parser')

        if 'amazon' in url:
            title = soup.find(id='productTitle')
            price = soup.find('span', {'class': 'a-offscreen'})
        elif 'flipkart' in url:
            title = soup.find('span', {'class': 'B_NuCI'})
            price = soup.find('div', {'class': '_30jeq3 _16Jk6d'})
        else:
            return {"error": "Unsupported website"}
        #print(f"Extracted Title: {title}")
        #print(f"Extracted Price: {price}")



        return {
            "title": title.get_text(strip=True) if title else "Title Not Found",
            "price": price.get_text(strip=True) if price else "Price Not Found"
        }

    except requests.RequestException as e:
        print("Request failed:", e)
        return {"error": "Request failed"}

def check_price():
    print(f"Checking prices at {datetime.datetime.now()}")
    for username, user_data in users.items():
    
        print(f"Checking for user: {username}")  # Debug log
        chat_id = user_data.get("chat_id")
        if not chat_id:
            print(f"Skipping {username}, no chat ID found.")
            continue

        for url, product in user_data.get("products", {}).items():
            print(f"Checking product: {product['title']}")  # Debug log

            new_price_data = get_price(url)
            print(f"Raw price extracted: {new_price_data['price']}")  # Debugging

            if new_price_data["price"] == "N/A":
                print(f"Could not fetch price for {product['title']}, skipping.")
                continue

            try:
                current_price = float(new_price_data["price"].replace("₹", "").replace(",", ""))
                desired_price = float(product["desired_price"])
            except ValueError:
                print(f"Invalid price format for {product['title']}, skipping.")
                continue
            last_price = users[username]["products"][url].get("current_price")
            if current_price <= float(desired_price) and current_price != last_price:
                message = f"Price Alert! {product['title']} is now {new_price_data['price']} (Target: ₹{desired_price})\n{url}"
                # print(f"Checking price for {url}: Current {current_price}, Desired {desired_price}")
                print(f"Chat ID for {username}: {chat_id}")

                # print(f"Sending alert to {username} at {chat_id}: {message}")  # Debug log
                send_telegram_message(chat_id,message)
            else:
                print(f"Price is still high. No alert sent.")
            # Update price in user data
            users[username]["products"][url]["current_price"] = current_price

    save_users()
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        chat_id = request.form['chat_id']
        email = request.form['email']

        if username in users:
            return "User already exists! Try another username."
        
        otp = str(random.randint(100000, 999999))
        otp_store[email] = otp  # Store OTP temporarily

        # Store user temporarily before confirmation
        session['pending_user'] = {
            "username": username,
            "password": generate_password_hash(password),
            "chat_id": chat_id,
            "email": email
        }

        # Send OTP email
        msg = Message("Your OTP Code", sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f"Your OTP code is: {otp}. It is valid for 5 minutes."
        print("Recipients:", msg.recipients)
        print("Sender:", msg.sender)


        try:
            mail.send(msg)
            print(f"OTP sent to: {email}")  # Debugging print
            return redirect('/verify_otp')
        except Exception as e:  # Catch all exceptions
            print(f"Error sending email: {e}")  # Debugging print
            return f"Error sending email: {e}", 500

    
    return render_template('register.html')
    #     users[username] = {
    #         "password": generate_password_hash(password),
    #         "chat_id": chat_id,
    #         "products": {}
    #     }
    #     save_users()
    #     return redirect('/login')
    
    # return render_template('register.html')
@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        email = session.get('pending_user', {}).get('email')
        user_otp = request.form.get('otp')

        if not email or email not in otp_store or otp_store[email] != user_otp:
            return "Invalid OTP!", 400

        user_data = session.pop('pending_user', None)  
        if not user_data:
            return "Session expired. Please register again.", 400

        users[user_data['username']] = {
            "password": user_data['password'],
            "chat_id": user_data['chat_id'],
            "email": user_data['email'],
            "products": {}
        }

        del otp_store[email]

        return redirect('/login')

    return render_template('verify.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username not in users or not check_password_hash(users[username]['password'], password):
            
            return render_template('login.html', error="Invalid username or password!")

        session['username'] = username
        print("Logged in as:", username)  # Debugging

        return redirect('/')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')

@app.route('/')
def home():
    if 'username' not in session:
        return redirect('/login')  # Redirect to login if not authenticated

    username = session['username']
    
    # Check if user exists in users
    if username not in users:
        session.pop('username', None)  # Remove invalid session
        return redirect('/login')  # Redirect to login

    return render_template('index.html', tracked_products=users[username]['products'])

  # Save updated price data
@app.route('/track', methods=['POST'])
def track():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    
    product_url = request.form.get("url")
    desired_price = request.form.get("desired_price")

    if not product_url or not desired_price:
        return "Both URL and Desired Price are required", 400
    
    try:
        desired_price = float(desired_price)
    except ValueError:
        return "Invalid price format", 400
    
    product_data = get_price(product_url)
    if "error" in product_data:
        return "Unsupported website", 400
    
    if username not in users:
        return "User not found", 400
    users[username]['products'][product_url] = {
        "title": product_data["title"],
        "desired_price": desired_price,
        "current_price": product_data["price"]
    }
    print(f"Saving product for {username}: {users[username]['products']}")
    save_users()
    return redirect('/')
###############################################################
#############################################################
@app.route('/test_scheduler')
def test_scheduler():
    check_price()
    return "Manual price check triggered!"


@app.route('/remove', methods=['POST'])
def remove():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    
    product_url = request.form.get("url")
    if product_url in users[username]['products']:
        del users[username]['products'][product_url]
        save_users()
    
    return redirect('/')
scheduler = BackgroundScheduler()

if not scheduler.running:  # Ensure it's not already running
    scheduler.add_job(check_price, 'interval', minutes=1)
    scheduler.start()
if __name__ == '__main__':
    app.run(debug=True)