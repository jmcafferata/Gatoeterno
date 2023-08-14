import cv2
import pytesseract
import json
import openai



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
def extract_details(text):

    #get openai api key from openai_api_key.txt
    with open('openai_api_key.txt', 'r') as f:
        openai.api_key = f.read()
    response = openai.ChatCompletion.create(
        model="gpt-4-0613",
        messages=[
            {"role":"system","content":"I will give you OCR-extracted text. identify the main columns and generate an array of item objects "},
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

    
