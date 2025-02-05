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
@app.route('/track', methods=['GET'])
def track():
    product_url = request.args.get("url")
    if not product_url:
        return jsonify({"error": "URL parameter is required"}), 400

    data = get_price(product_url)
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
