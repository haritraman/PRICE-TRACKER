from flask import Flask,render_template, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def get_price(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"}
    
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
@app.route('/')
def home():
    return render_template('index.html')
@app.route('/about')
def about():
    return "This is the About page."
@app.route('/track', methods=['GET','POST'])
def track():
    if request.method=='POST':
        product_url=request.form.get("url")
        desired_price = request.form.get("desired_price")
    else:
        product_url = request.args.get("url")
        desired_price = request.args.get("desired_price")

    if not product_url or not desired_price:
        return render_template("index.html",error= "Both URL and Desired Price are required"),400
    
    try:
        desired_price = float(desired_price)  # Convert input to float
    except ValueError:
        return render_template("index.html",error="Invalid price format"),400

    data = get_price(product_url)

    if data["price"] == "N/A":
        return render_template("index.html",error= "Could not fetch the price"),400
    try:
        current_price = float(data["price"].replace("₹", "").replace(",", "").strip())
    except ValueError:
        return render_template("index.html", error="Error parsing price"), 400  # Return a valid tuple
    

    # Check price condition
    if current_price <= desired_price:
        message = f"Good news! The price of '{data['title']}' has dropped to {current_price}!"
    else:
        message = f"Current price of '{data['title']}' is {current_price}. Waiting for {desired_price}."

    return render_template("index.html",title=data["title"], current_price= current_price, desired_price= desired_price, message= message)

if __name__ == '__main__':
    app.run(debug=True)
