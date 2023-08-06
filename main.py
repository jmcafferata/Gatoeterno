from flask import Flask, render_template, request, jsonify, send_from_directory
import openai
import pandas as pd
from openai.embeddings_utils import get_embedding
import numpy as np
from openai.embeddings_utils import cosine_similarity
from pathlib import Path
import os
from datetime import datetime
from io import StringIO
from ast import literal_eval
import pytz
import requests
timezone = pytz.timezone('America/Argentina/Buenos_Aires')
import json
import cv2
import pytesseract


app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():

    return render_template('index.html')

@app.route('/add_selection', methods=['POST'])
def add_selection():
    try:
        selection = request.get_json(force=True)
        with open('selection.json', 'w', encoding='utf-8') as f:
            json.dump(selection, f)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

@app.route('/get_<data>', methods=['GET'])
def get_data(data):
    with open(data+'.json', 'r', encoding='utf-8') as f:
        data = f.read()
    return data


@app.route('/add_to_stock', methods=['POST'])
def add_to_stock():
    try:
        # Read the selection
        with open('selection.json', 'r', encoding='utf-8') as f:
            selection = json.load(f)

        # Read the stock
        with open('stock.json', 'r', encoding='utf-8') as f:
            stock = json.load(f)

        for book in selection:
            isbn = book['isbn']
            cantidad = book['cantidad']
            
            # Try to find the book in the stock based on ISBN
            found = next((b for b in stock if b['isbn'] == isbn), None)

            if found:
                found['cantidad'] += cantidad
            else:
                stock.append(book)

        # Write the updated stock back to stock.json
        with open('stock.json', 'w', encoding='utf-8') as f:
            json.dump(stock, f, ensure_ascii=False, indent=4)

        # Clean up selection.json
        with open('selection.json', 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)

        return jsonify({'status': 'success'})
    except Exception as e:
        print(e)
        return jsonify({'status': 'error', 'error': str(e)})

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part in the request.'}), 400
    image = request.files['file']
    
    # Check if the file is empty
    if image.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file.'}), 400
    
    image_path = 'image.jpeg'
    image.save(image_path)
    
    extracted_text = ocr_image(image_path)
    items = extract_details(extracted_text)
    
    return jsonify({'status': 'success', 'items': items})

           

@app.route('/get_details_by_isbn/<isbn>', methods=['GET'])
def get_book_details_by_isbn(isbn):
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    response = requests.get(url)
    data = response.json()

    if f"ISBN:{isbn}" in data:
        book_data = data[f"ISBN:{isbn}"]
        
        title = book_data.get('title', 'N/A')
        authors = ', '.join([author['name'] for author in book_data.get('authors', [])])
        publishers = ', '.join([publisher['name'] for publisher in book_data.get('publishers', [])])
        publish_date = book_data.get('publish_date', 'N/A')
        
        return jsonify({
            'Title': title,
            'Authors': authors,
            'Publishers': publishers,
            'Publish Date': publish_date
        })
    else:
        return jsonify({"error": "No data found for the provided ISBN."}), 404

def ocr_image(image_path):
    # Read the image using OpenCV
    img = cv2.imread(image_path)
    
    # Convert the image to grayscale (this can improve OCR accuracy)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Extract text from the image using pytesseract
    extracted_text = pytesseract.image_to_string(gray)
    
    return extracted_text

def extract_details(text):
    #get openai api key from openai_api_key.txt
    with open('openai_api_key.txt', 'r') as f:
        openai.api_key = f.read()
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role":"system","content":"I will give you OCR-extracted text. generate a json of 'items' and get only isbn, cantidad, and precio. A typical price is 2.900,00"},
            {"role":"user","content":text},
            {"role":"assistant","content":"here's the json:\n"}
        ])
    return response.choices[0].message.content


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)