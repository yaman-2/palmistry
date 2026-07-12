import requests
import io
from PIL import Image

# Create dummy image
img = Image.new('RGB', (100, 100), color = 'red')
img_byte_arr = io.BytesIO()
img.save(img_byte_arr, format='JPEG')
img_byte_arr = img_byte_arr.getvalue()

url = "https://palmistry-nine.vercel.app/process_palm"
files = {'image_file': ('palm_scan.jpg', img_byte_arr, 'image/jpeg')}
data = {'session_id': 'test-session'}

try:
    print(f"Sending POST to {url}...")
    response = requests.post(url, files=files, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
