from flask import Flask, render_template, request, redirect
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler

from dotenv import load_dotenv
import os
app = Flask(__name__)

# Telegram Bot Details


# Load environment variables from .env file
load_dotenv()

# Get the Telegram Bot Token
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = "1804074852"

# Store tracking details
tracked_products = {}

def send_telegram_message(message):
    """Send a notification to Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, params=params)

def get_price(url):
    """Scrape price from Amazon or Flipkart."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    if 'amazon' in url:
        title = soup.find(id='productTitle')
        price = soup.find('span', {'class': 'a-offscreen'})
    elif 'flipkart' in url:
        title = soup.find('span', {'class': 'B_NuCI'})
        price = soup.find('div', {'class': '_30jeq3 _16Jk6d'})
    else:
        return {"error": "Unsupported website"}
    
    return {
        "title": title.get_text(strip=True) if title else "N/A",
        "price": price.get_text(strip=True) if price else "N/A"
    }

def check_price():
    """Check price every hour and send notification if price drops."""
    print("Checking prices...")
    for url, details in tracked_products.items():
        data = get_price(url)
        if data["price"] == "N/A":
            continue  # Skip if price not found

        try:
            current_price = float(data["price"].replace("₹", "").replace(",", "").strip())
        except ValueError:
            continue  # Skip if price conversion fails

        tracked_products[url]["current_price"] = current_price  # Update current price

        # Check if current price is lower than or equal to desired price
        if current_price <= details["desired_price"]:
            message = f"🔥 Price Drop Alert! 🔥\n{data['title']}\nCurrent Price: ₹{current_price}\nBuy Now: {url}"
            send_telegram_message(message)

@app.route('/')
def home():
    return render_template('index.html', tracked_products=tracked_products)

@app.route('/track', methods=['POST'])
def track():
    """Track a new product."""
    product_url = request.form.get("url")
    desired_price = request.form.get("desired_price")

    if not product_url or not desired_price:
        return render_template("index.html", error="Both URL and Desired Price are required", tracked_products=tracked_products), 400
    
    try:
        desired_price = float(desired_price)
    except ValueError:
        return render_template("index.html", error="Invalid price format", tracked_products=tracked_products), 400

    # Get initial product details
    product_data = get_price(product_url)
    if "error" in product_data:
        return render_template("index.html", error="Unsupported website", tracked_products=tracked_products), 400

    tracked_products[product_url] = {
        "title": product_data["title"],
        "desired_price": desired_price,
        "current_price": product_data["price"]
    }
    check_price()    

    return redirect('/')

@app.route('/remove', methods=['POST'])
def remove():
    """Remove a tracked product."""
    product_url = request.form.get("url")
    if product_url in tracked_products:
        del tracked_products[product_url]
    return redirect('/')

# Scheduler to check prices every hour
scheduler = BackgroundScheduler()
scheduler.add_job(check_price, 'interval', minutes=30)
scheduler.start()

if __name__ == '__main__':
    app.run(threaded=True)
