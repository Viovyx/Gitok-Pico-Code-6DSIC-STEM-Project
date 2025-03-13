import adafruit_requests, os, wifi, ssl, socketpool

# API
headers = {"X-API-KEY":os.getenv('API_KEY')}
api_base_url = "https://api.tapgate.tech/api.php/records/"

def GetUserId(email):
    api_url = api_base_url + f"users?filter=Email,eq,{email}"
    with requests.get(api_url, headers=headers) as response:
        response = response.json()['records']
    
        if len(response) > 0:
            user = response[0]
            return user["id"]
        
# Connect to WiFi
print(f"[WIFI] Connecting to WiFi ({os.getenv('WIFI_SSID')})")
wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASS"))
print("[WIFI] Connected!")

# Create socketpool
pool = socketpool.SocketPool(wifi.radio)

# Requests
requests = adafruit_requests.Session(pool, ssl.create_default_context())

# User id
while True:
    email = input("Please enter the email of the user who this card belongs to: ")
    user_id = GetUserId(email)
    if user_id:
        print(f"This found email! User_id = {user_id}")
    else:
        print("This email does not exists!")
        