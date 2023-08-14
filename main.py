from flask import Flask, render_template, request, jsonify, send_from_directory, Blueprint
import openai
import pytz
import requests
timezone = pytz.timezone('America/Argentina/Buenos_Aires')
import json
import cv2
import pytesseract



app = Flask(__name__)
# bp = Blueprint('audiont', __name__, template_folder='templates')

# FOR DEBUG 👇
bp = Blueprint('audiont', __name__, template_folder='templates', static_folder='static', static_url_path='/static')


# Show index.html
@bp.route('/', methods=['GET'])
def index():

    return render_template('index.html')

# Add data to json file
@bp.route('/add_<dataName>', methods=['POST'])
def add_selection(dataName):
    try:
        data = request.get_json(force=True)
        with open(dataName+'.json', 'w', encoding='utf-8') as f:
            json.dump(data, f)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

# Get data from json file
@bp.route('/get_<data>', methods=['GET'])
def get_data(data):
    with open(data+'.json', 'r', encoding='utf-8') as f:
        data = f.read()
    return data

# Update data to json file
@bp.route('/update_<dataName>/<idName>/<id>/<property>/<value>', methods=['POST'])
def update_data(dataName, idName,id, property, value):
    try:
        # Read the data
        with open(dataName+'.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Find the book in the data based on ISBN
        found = next((b for b in data if b[idName] == id), None)

        if found:
            # if the property is a number, keep the value as number, not string
            property_type = type(found[property])
            if property_type == int or property_type == float:
                value = property_type(value)
            # if it's boolean or a string that says true of false, convert the string to boolean
            elif property_type == bool or (property_type == str and (value == 'true' or value == 'false')):
                value = True if value == 'true' else False

            found[property] = value
        else:
            return jsonify({'status': 'error', 'error': 'Book not found in the data.'})

        # Write the updated data back to json file
        with open(dataName+'.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})
    
# Empty data from json file
@bp.route('/empty_<dataName>', methods=['POST'])
def empty_data(dataName):
    with open(dataName+'.json', 'w', encoding='utf-8') as f:
        json.dump([], f)
    return jsonify({'status': 'success'})

@bp.route('/add_to_stock', methods=['POST'])
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

# Upload image to server
@bp.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file part in the request.'}), 400
        image = request.files['file']
        
        # Check if the file is empty
        if image.filename == '':
            return jsonify({'status': 'error', 'message': 'No selected file.'}), 400
        
        image_path = 'image.jpeg'
        image.save(image_path)

        # get prompt from form
        prompt = request.form['prompt']
        
        extracted_text = ocr_image(image_path)
        items_json = extract_details(extracted_text, prompt)
        # for each item, add the property "consignacion" as false
        for item in items_json:
            item['consignacion'] = False
 
        # replace selection.json with items_json
        with open('selection.json', 'w', encoding='utf-8') as f:
            json.dump(items_json, f, ensure_ascii=False, indent=4)
        return jsonify({'status': 'success', 'message': 'Image uploaded successfully.'})
    except Exception as e:
        print(e)
        return jsonify({'status': 'error', 'error': str(e)})

# Get book details by ISBN
@bp.route('/get_details_by_isbn/<isbn>', methods=['GET'])
def get_book_details_by_isbn(isbn):
    try:
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
                'titulo': title,
                'autor': authors,
                'editorial': publishers,
                'fecha': publish_date
            })
        else:
            return jsonify({"error": "No data found for the provided ISBN."}), 404
    except Exception as e:
        print(e)
        return jsonify({
                'titulo': '<Agregar título>',
                'autor': '<Agregar autores>',
                'editorial': '<Agregar editoriales>',
                'fecha': '<Agregar fecha de publicación>'
            })

# OCR uploaded image
def ocr_image(image_path):
    # Read the image using OpenCV
    img = cv2.imread(image_path)
    
    # Convert the image to grayscale (this can improve OCR accuracy)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Extract text from the image using pytesseract
    extracted_text = pytesseract.image_to_string(gray)
    print("Extracted text: ", extracted_text)
    
    return extracted_text

# Extract details from OCR text
def extract_details(text,prompt):

    #get openai api key from openai_api_key.txt
    with open('openai_api_key.txt', 'r') as f:
        openai.api_key = f.read()
    
    default_prompt = "generate an array of item objects and get only isbn, titulo, autor, editorial, precio (as float) and  cantidad (as int). if some of the fields is absent replace with N/A, and clean up the text so it looks nice. A typical price is 2900.00"

    print("Prompt: ", prompt)

    # if prompt is empty, use default prompt
    if prompt == "":
        prompt = default_prompt

    response = openai.ChatCompletion.create(
        model="gpt-4-0613",
        messages=[
            {"role":"system","content":"Te voy a dar texto extraído con OCR. Realizar la siguiente acción: "+prompt},
            {"role":"user","content":text},
            {"role":"assistant","content":"here's the array:\n"}
        ])
    response_text = response.choices[0].message.content
    # json loads the string into a dictionary
    print(response_text)
    # get only the text from the first '[' to the last ']'
    response_text = response_text[response_text.find('['):response_text.rfind(']')+1]
    response_json = json.loads(response_text)

    print(response_json)
    return response_json

    



if __name__ == '__main__':
    app.run(debug=True)