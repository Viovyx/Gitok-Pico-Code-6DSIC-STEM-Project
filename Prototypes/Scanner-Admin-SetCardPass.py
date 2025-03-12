import board, time, math, json, requests
import busio, pwmio, digitalio
import os, ssl, socketpool, wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_character_lcd.character_lcd as characterlcd
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_A, MIFARE_CMD_AUTH_B


# -------------
# Functions
# -------------
def InitiateNFC(i2c_sda: Pin, i2c_scl: Pin):
    print("Initiating pn532...")
    i2c = busio.I2C(scl=i2c_scl, sda=i2c_sda)
    pn532 = PN532_I2C(i2c, debug=False)
    ic, ver, rev, support = pn532.firmware_version
    print(f"Found pn532 with firmware version: {ver}.{rev}")
    pn532.SAM_configuration()
    
    return pn532

def StringToByteArray(input_str: str, max_len: int):
    if len(input_str) > max_len:
        print(f"ERROR: Length is longer than the max ({max_len})! \n")
        return 
    data = [ord(char) for char in input_str]
    for i in range(max_len - len(data)):
        data.append(0)
    data_bytes = bytearray(data)
    
    return data_bytes

def BitsToByteArray(length: int):
    bits = []
    for i in range(length):
        bit = None
        while not bit:
            user_bit = input(f"Enter bit {i+1}: ")
            try:
                if 0 <= int(user_bit) <= 255:
                    bit = int(user_bit)
                else:
                    raise Exception()
            except:
                print("ERROR: Please enter an integer between 0-255.")
        bits.append(bit)
    bytes = bytearray(bits)

    return bytes

def GetCardUID(scanner: PN532_I2C):
    print("[DEBUG] Waiting for card")
    while True:
        mqtt_client.loop()
        uid = scanner.read_passive_target(timeout=0.5)
        if uid is not None:
            break
    print(f"[DEBUG] Found card with UID: {[i for i in uid]}")
    return uid

def AuthBlock(scanner: PN532_I2C, block: int, key: bytearray, b: bool = False):
    uid = GetCardUID(scanner=scanner)
    print(f"Authenticating block {block} ...")
    authenticated = scanner.mifare_classic_authenticate_block(uid, block, MIFARE_CMD_AUTH_B if b else MIFARE_CMD_AUTH_A, key)
    if authenticated:
        print("Authentication SUCCESFUL! \n")
    else:
        print("Authentication FAILED!")
        
    return authenticated 

def WriteBlock(scanner: PN532_I2C, block: int, key_b: bytearray, data: bytearray):
    authenticated = AuthBlock(scanner=scanner, block=block, key=key_b, b=True)
    if authenticated:
        print(f"Writing data to block {block}...")
        try:
            scanner.mifare_classic_write_block(block, data)
            print(f"Wrote to block {block}")
            return True 
        except:
            print("ERROR: Something went wrong while writing the data.")
            return False 

# API
def GetUserId(email):
    api_url = api_base_url + f"users?filter=Email,eq,{email}"
    response = requests.get(api_url, headers=headers)
    response = response.json()['records']
    
    if len(response) > 0:
        user = response[0]
        return user["id"]

# CardPass
def SetCardPass(scanner, block, key_b, new_key_a, new_key_b, access_bits, user_id, card_pass):
    lcd.clear()
    lcd.message = "Scan Card...\n" + "Hold Firmly!"

    # Creating and Writing new trailer
    trailer = new_key_a + access_bits + new_key_b
    sector = math.ceil((block+1)/4)
    sector_block = 4*sector - 1

    print(f"Writing new trailer for sector {sector}...")
    if WriteBlock(scanner=scanner, block=sector_block, key_b=key_b, data=trailer):
        print(f"[SUCCESS] Wrote new trailer for sector {sector} (block {sector_block})")
        print("Key A\t Access Bits\t Key B")
        print(f"{new_key_a}\t {access_bits}\t {new_key_b}")
    else:
        print(f"[ERROR] Could not write trailer for sector {sector} (block {sector_block})")
        return
        
    # Writing CardPass
    if WriteBlock(scanner=scanner, block=block, key_b=new_key_b, data=card_pass):
        print(f"[SUCCESS] Wrote Card Pass to block {block}")
    else:
        print(f"[ERROR] Could not write Card Pass to block {block}")

    # Send Data to MQTT
    # Getting UID of card
    card_pass_feed = aio_user + "/feeds/scanner.setcardpass"
    card_uid = f"{[i for i in GetCardUID(scanner=nfc)]}".replace(" ", "")
    mqtt_client.publish(card_pass_feed, {"uid":card_uid, "pass":card_pass_text, "user":user_id})

# Buzzer Sounds
def toneSuccess():
    buzzer.duty_cycle=2**15
    buzzer.frequency = 850
    time.sleep(0.06) 
    buzzer.duty_cycle=0
    time.sleep(0.06)

def toneFail():
    buzzer.duty_cycle=2**15
    buzzer.frequency = 300
    time.sleep(0.3)
    buzzer.duty_cycle=0


# ---------------
# Network + MQTT
# ---------------

# MQTT Functions
def connect(mqtt_client, userdata, flags, rc):
    print("[MQTT] Connected to MQTT Broker!")
    print(f"[MQTT] Flags: {flags} ; RC: {rc}")

def disconnect(mqtt_client, userdata, rc):
    print("[MQTT] Disconnected from MQTT Broker!")

def subscribe(mqtt_client, userdata, topic, granted_qos):
    print(f"[MQTT] Subscribed to {topic} with QOS level {granted_qos}")

def unsubscribe(mqtt_client, userdata, topic, pid):
    print(f"[MQTT] Unsubscribed from {topic} with PID {pid}")

def publish(mqtt_client, userdata, topic, pid):
    print(f"[MQTT] Published to {topic} with PID {pid}")

def message(client, topic, message):
    print(f"[MQTT] New message on topic {topic}: {message.payload.decode()}")


# Connect to WiFi
print(f"[WIFI] Connecting to WiFi ({os.getenv('WIFI_SSID')})")
wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASS"))
print("[WIFI] Connected!")

# Create socketpool
pool = socketpool.SocketPool(wifi.radio)

# Get adafruit.io credentials
aio_user = os.getenv("AIO_USER")
aio_key = os.getenv("AIO_KEY")
aio_broker = os.getenv("BROKER")
aio_port = os.getenv("PORT")

# API
headers = {"X-API-KEY":os.getenv('API_KEY')}
api_base_url = "https://api.tapgate.tech/api.php/records/"

# Set up MQTT Client
mqtt_client = MQTT.MQTT(
    broker=aio_broker,
    username=aio_user,
    password=aio_key,
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Connect callback handlers to mqtt_client
mqtt_client.on_connect = connect
mqtt_client.on_disconnect = disconnect
mqtt_client.on_subscribe = subscribe
mqtt_client.on_unsubscribe = unsubscribe
mqtt_client.on_publish = publish
mqtt_client.on_message = message

# Create MQTT Connection
print(f"[MQTT] Attempting to connect to {mqtt_client.broker}")
mqtt_client.connect()


# -------------
# Pin Setup
# -------------

# NFC Setup
nfc_sda = board.GP14
nfc_scl = board.GP15
nfc = InitiateNFC(i2c_sda=nfc_sda, i2c_scl=nfc_scl)
default_access_bits = [8,119,143,255]

# LCD Setup
# PIN Setup
lcd_rs = digitalio.DigitalInOut(board.GP0)
lcd_en = digitalio.DigitalInOut(board.GP1)
lcd_d4 = digitalio.DigitalInOut(board.GP2)
lcd_d5 = digitalio.DigitalInOut(board.GP3)
lcd_d6 = digitalio.DigitalInOut(board.GP4)
lcd_d7 = digitalio.DigitalInOut(board.GP5)
lcd_backlight = digitalio.DigitalInOut(board.GP6)
# Contrast Setup
contrast = pwmio.PWMOut(board.GP7, frequency=5000, duty_cycle=0)
contrast_percentage = 60
contrast.duty_cycle = int(65535 * (1 - contrast_percentage/100))
# Display size
lcd_columns = 16
lcd_rows = 2
# Initialize lcd
lcd = characterlcd.Character_LCD_Mono(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows, lcd_backlight)

# Button Setup
button_up = DigitalInOut(board.GP10)
button_down = DigitalInOut(board.GP11)
button_confirm = DigitalInOut(board.GP12)

button_up.switch_to_input(pull=digitalio.Pull.DOWN)
button_down.switch_to_input(pull=digitalio.Pull.DOWN)
button_confirm.switch_to_input(pull=digitalio.Pull.DOWN)

# Buzzer Setup
buzzer = pwmio.PWMOut(board.GP13, variable_frequency=True)


# -------------
# Program
# -------------
toneSuccess()
lcd.backlight = True

# Requesting needed info
default_block = 16
default_key = [255,255,255,255]
default_key_a = os.getenv("CARD_KEY_A")
default_key_b = os.getenv("CARD_KEY_B")
default_access_bits = [8,119,143,255]

lcd.clear()
lcd.message = "Follow instructions\nin terminal..."
print("==============================================================")
print(" Set KeyCard Password by following these steps.")
print(" Press ENTER without entering anything to use default values.")
print(" Default values are shown between square brackets [x].")
print("==============================================================")

# Block
block = None 
while not block:
    user_input = input(f"Enter the block number [{default_block}]: ")
    try:
        block = int(user_input)
    except:
        if user_input != "":
            print("ERROR: Please enter an integer.")
        else:
            block = default_block

# Original Key
key = None 
while not key:
    user_input = input(f"Enter original key B (Enter 'b' for bits mode) [{default_key}]: ")
    if user_input.lower() == "b":
        key = BitsToByteArray(length=6)
    else:
        if user_input != "":
            key = StringToByteArray(input_str=user_input, max_len=6)
        else:
            key = bytearray(default_key)

# New Keys
new_key_a = None
while not new_key_a:
    user_input = input(f"Enter new key A (Enter 'b' for bits mode) [{default_key_a}]: ")
    if user_input.lower() == "b":
        new_key_a = BitsToByteArray(length=6)
    else:
        if user_input != "":
            new_key_a = StringToByteArray(input_str=user_input, max_len=6)
        else:
            new_key_a = StringToByteArray(default_key_a, max_len=6)

new_key_b = None
while not new_key_b:
    user_input = input(f"Enter new key B (Enter 'b' for bits mode) [{default_key_b}]: ")
    if user_input.lower() == "b":
        new_key_b = BitsToByteArray(length=6)
    else:
        if user_input != "":
            new_key_b = StringToByteArray(input_str=user_input, max_len=6)
        else:
            new_key_b = StringToByteArray(default_key_b, max_len=6)

# Access Bits
access_bits = None
while not access_bits:
    user_input = input(f"Use the default access bits [{default_access_bits}]? (Y/n): ")
    if user_input.lower() == "n":
        access_bits = BitsToByteArray(length=4)
    else:
        access_bits = bytearray(default_access_bits)

# User id
user_id = None
while not user_id:
    email = input("Please enter the email of the user who this card belongs to: ")
    user_id = GetUserId(email)
    if not user_id:
        print("This email does not exists!")

# Card Password
card_pass = None
while not card_pass:
    card_pass_text = input("Please enter the new Card Password: ")
    card_pass = StringToByteArray(input_str=card_pass_text, max_len=16)

print("===================================")
print(" Info Confirmed!")
print(" Follow instruction on scanner...")
print("===================================")
SetCardPass(scanner=nfc, block=block, key_b=key, new_key_a=new_key_a, new_key_b=new_key_b, access_bits=access_bits, user_id=user_id, card_pass=card_pass)

lcd.clear()
lcd.message = f"Password Set!\n{card_pass}"
lcd.backlight = False