import cv2
import json
import re
import tempfile
from passporteye import read_mrz
import easyocr
import pytesseract

# Update this path to match your Tesseract installation
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # 👈 Double-check this path!

# Initialize EasyOCR reader once for better performance
reader = easyocr.Reader(['en'])

def capture_image():
    """Capture image from webcam when 's' is pressed."""
    cap = cv2.VideoCapture(0)
    print("Press 's' to capture image, 'q' to quit...")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow('Live Capture', frame)
        key = cv2.waitKey(1)
        if key == ord('s'):
            break
        elif key == ord('q'):
            frame = None
            break
    cap.release()
    cv2.destroyAllWindows()
    return frame

def process_passport(image):
    """Process image to extract passport data using PassportEye."""
    #with tempfile.NamedTemporaryFile(suffix='.jpg') as temp:
        #cv2.imwrite(temp.name, image)
    mrz = read_mrz(image)
    if mrz:
        mrz_data = mrz.to_dict()
        return {
            "type": "International Passport",
            "data": {
                "surname": mrz_data.get('surname', ''),
                "given_names": mrz_data.get('names', ''),
                "passport_number": mrz_data.get('number', ''),
                "nationality": mrz_data.get('nationality', ''),
                "date_of_birth": mrz_data.get('date_of_birth', ''),
                "sex": mrz_data.get('sex', ''),
                "expiration_date": mrz_data.get('expiration_date', ''),
                "personal_number": mrz_data.get('personal_number', '')
            }
        }
    return None


def process_nin(image):
    """Process image to extract NIN slip data using EasyOCR and regex."""
    #rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = reader.readtext(image, detail=0, paragraph=True)
    text = '\n'.join(results)
    
    # Extract NIN (11 digits)
    nin = re.search(r'\b\d{11}\b', text)
    # Extract full name (case-insensitive, multi-line)
    name = re.search(r'(?:name|full name)[:\s]*([^\n]+)', text, re.IGNORECASE)
    # Extract gender
    gender = re.search(r'(?:gender|sex)[:\s]*([^\n]+)', text, re.IGNORECASE)
    # Extract birth date
    #birth_date = re.search(r'(?:date of birth|dob)[:\s]*([^\n]+)', text, re.IGNORECASE)
    
    return {
        "type": "NIN Slip",
        "data": {
            "nin": nin.group(0) if nin else None,
            "full_name": name.group(1).strip() if name else None,
            "gender": gender.group(1).strip() if gender else None,
            #"date_of_birth": birth_date.group(1).strip() if birth_date else None
        }
    }

def main():
    #image = capture_image()
    ###if image is None:
        #print("No image captured.")
        #return
    
    # Attempt Passport processing
    passport_data = process_passport("NIMC ID CARD_20230809_124805_991_70 (1).jpg")
    if passport_data:
        output = passport_data
    else:
        # Fallback to NIN processing
        output = process_nin("NIMC ID CARD_20230809_124805_991_70 (1).jpg")
    
    # Save to JSON
    with open('output.json', 'w') as f:
        json.dump(output, f, indent=2)
    print("Extracted Data:")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()