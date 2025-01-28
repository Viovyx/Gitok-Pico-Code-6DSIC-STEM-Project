import board
import busio
import pwmio
import digitalio
import time
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
        toneFail()
        lcd.clear()
        lcd.message = "ERROR\nCheck console"
        print(f"ERROR: Length is longer than the max ({max_len})! \n")
        return 
    data = [ord(char) for char in input_str]
    for i in range(max_len - len(data)):
        data.append(0)
    data_bytes = bytearray(data)
    
    return data_bytes


def BytesToByteArray(length: int):
    bytes_array = []
    for i in range(length):
        byte = None
        while not (byte == 0 or byte):
            user_byte = input(f"Enter byte {i+1}: ")
            try:
                if 0 <= int(user_byte) and int(user_byte) <= 255:
                    byte = int(user_byte)
                else:
                    raise Exception()
            except:
                toneFail()
                lcd.clear()
                lcd.message = "ERROR\nCheck console"
                print("ERROR: Please enter an integer between 0-255.")
        bytes_array.append(byte)

    return bytearray(bytes_array)


def HexArrayToString(array: []):
    array_over = []
    for i in array:
        if i == '0':
            array_over.append(i)
        if len(array_over)%2 != 0:
            array.append('0')
    try:
        data_string = bytearray.fromhex(''.join(array)).decode()
    except:
        return "<ERROR>"
    
    return data_string


def GetCardUID(scanner: PN532_I2C):
    lcd.clear()
    lcd.message = "Waiting for card"
    print("Waiting for card")
    while True:
        uid = scanner.read_passive_target(timeout=0.5)
        if uid is not None:
            break
    print(f"\nFound card with UID: {[i for i in uid]}")
    
    return uid
    

def AuthBlock(scanner: PN532_I2C, block: int, key: bytearray, b: bool = False):
    uid = GetCardUID(scanner=scanner)
    print(f"Authenticating block {block} ...")
    authenticated = scanner.mifare_classic_authenticate_block(uid, block, MIFARE_CMD_AUTH_B if b else MIFARE_CMD_AUTH_A, key)
    if authenticated:
        print("Authentication SUCCESFUL! \n")
    else:
        lcd.clear()
        lcd.message = "ERROR:\nCheck console"
        print("Authentication FAILED!")
        
    return authenticated 


def ReadBlock(scanner: PN532_I2C, block: int, key_a: bytearray):
    authenticated = AuthBlock(scanner=scanner, block=block, key=key_a)
    if authenticated:
        print(f"Reading block {block}...")
        try:
            value = [hex(x)[2:] for x in scanner.mifare_classic_read_block(block)]
            return value
        except:
            toneFail()
            lcd.clear()
            lcd.message = "ERROR\nCheck console"
            print("ERROR: Something went wrong while reading.")
            return False 


def WriteBlock(scanner: PN532_I2C, block: int, key_b: bytearray, data: bytearray):
    authenticated = AuthBlock(scanner=scanner, block=block, key=key_b, b=True)
    if authenticated:
        print(f"Writing data to block {block}...")
        try:
            scanner.mifare_classic_write_block(block, data)
            lcd.clear()
            lcd.message = "SUCCESS:\nData Written"
            print(f"Wrote to block {block}")
            return True 
        except:
            lcd.clear()
            lcd.message = "ERROR:\nCheck console"
            print("ERROR: Something went wrong while writing the data.")
            return False 
            
            
def CreateNewTrailer(scanner: PN532_I2C, sector: int,  key_b: bytearray, new_key_a: bytearray, new_key_b: bytearray, access_bits: bytearray):
    trailer = new_key_a + access_bits + new_key_b
    block = 4*sector - 1
    authenticated = AuthBlock(scanner=scanner, block=block,  key=key_b, b=True)
    if authenticated:
        print(f"Writing new trailer for sector {sector}...")
        if WriteBlock(scanner=scanner, block=block, key_b=key_b, data=trailer):
            lcd.clear()
            lcd.message = "SUCCESS:\nTrailer Created"
            print("Key A, Access Bits, Key B")
            print(f"{new_key_a}, {access_bits}, {new_key_b}")
        else:
            lcd.clear()
            lcd.message = "ERROR:\nCheck console"

# Button + lcd nav funtions
def wait_for_button_press():
    while True:
        if button_up.value or button_down.value or button_confirm.value:
            time.sleep(0.1)
            if button_up.value:
                return "up"
            if button_down.value:
                return "down"
            if button_confirm.value:
                return "confirm"

def navigate_options(options):
    index = 0
    while True:
        lcd.clear()
        lcd.message = "Select Action:\n"
        lcd.message += options[index]
        action = wait_for_button_press()
        if action == "up":
            toneSuccess()
            index = (index - 1) % len(options)
        elif action == "down":
            toneSuccess()
            index = (index + 1) % len(options)
        elif action == "confirm":
            lcd.clear()
            toneSuccess()
            return index

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

# MQTT Callback Functions
def connect(mqtt_client, userdata, flags, rc):
    print("Connected to MQTT Broker!")
    print(f"Flags: {flags}\n RC: {rc}")

def disconnect(mqtt_client, userdata, rc):
    print("Disconnected from MQTT Broker!")

def subscribe(mqtt_client, userdata, topic, granted_qos):
    print(f"Subscribed to {topic} with QOS level {granted_qos}")

def unsubscribe(mqtt_client, userdata, topic, pid):
    print(f"Unsubscribed from {topic} with PID {pid}")

def publish(mqtt_client, userdata, topic, pid):
    print(f"Published to {topic} with PID {pid}")

def message(client, topic, message):
    # Handle incomming MQTT messages here
    print(f"New message on topic {topic}: {message}")


# ---------------
# Network + MQTT
# ---------------

# Connect to WiFi
print("Connecting to WiFi")
wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASS"))
print("Connected!")

# Create socketpool
pool = socketpool.SocketPool(wifi.radio)

# Get adafruit.io credentials
aio_user = os.getenv("AIO_USER")
aio_key = os.getenv("AIO_KEY")
aio_broker = os.getenv("BROKER")
aio_port = os.getenv("PORT")

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

# Setup topics here
topics = ["test1", "test2"]


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

options = [
    "Read Block",
    "Write Block",
    "Change Trailer",
    "Get Card UID",
    "Quit Program"
]

# MQTT Connection
print("Attempting to connect to %s" % mqtt_client.broker)
mqtt_client.connect()

## TODO: add topics subscribing etc.

running = True
while running:
    lcd.backlight = True
    option = navigate_options(options)
    action = ["r", "w", "t", "u", "q"][option]

    if action.lower() == "r":  # Reading option
        lcd.clear()
        lcd.message = "Enter input:\nBlock Number"
        block = None 
        while not block:
            user_input = input("Enter the block number: ")
            try:
                block = int(user_input)
            except:
                toneFail()
                lcd.clear()
                lcd.message = "ERROR\nCheck console"
                print("ERROR: Please enter an integer.")
        
        lcd.clear()
        lcd.message = "Enter input:\nKey A"
        key = None 
        while not key:
            user_input = input(f"Enter key A for sector {int(block/4)+1} (Enter 'b' for byte mode): ")
            if user_input.lower() == "b":
                key = BytesToByteArray(length=6)
            else:
                key = StringToByteArray(input_str=user_input, max_len=6)
        
        data = ReadBlock(scanner=nfc, block=block, key_a=key)
        if data:
            print(f"Data (bytes in hex): {data}")  
            print(f"Data (text): {HexArrayToString(array=data)}")
            lcd.clear()
            lcd.message = f"Data:\n{HexArrayToString(array=data)}"

    elif action.lower() == "w":  # Writing option
        lcd.clear()
        lcd.message = "Enter input:\nBlock Number"
        block = None 
        while not block:
            user_input = input("Enter the block number: ")
            try:
                block = int(user_input)
            except:
                toneFail()
                lcd.clear()
                lcd.message = "ERROR\nCheck console"
                print("ERROR: Please enter an integer.")
        
        lcd.clear()
        lcd.message = "Enter input:\nKey B"
        key = None 
        while not key:
            user_input = input(f"Enter key B for sector {int(block/4)+1} (Enter 'b' for byte mode): ")
            if user_input.lower() == "b":
                key = BytesToByteArray(length=6)
            else:
                key = StringToByteArray(input_str=user_input, max_len=6)
        
        lcd.clear()
        lcd.message = "Enter input:\nData"
        data = None
        while not data:
            user_input = input(f"Enter the data to write to block {block}: ")
            data = StringToByteArray(input_str=user_input, max_len=16)
        
        WriteBlock(scanner=nfc, block=block, key_b=key, data=data)

    elif action.lower() == "t":  # Change sector trailer option
        lcd.clear()
        lcd.message = "Enter input:\nSector Number"
        sector = None
        while not sector:
            user_input = input("Enter the sector number: ")
            try:
                sector = int(user_input)
            except:
                toneFail()
                lcd.clear()
                lcd.message = "ERROR\nCheck console"
                print("ERROR: Please enter an integer.")
        
        lcd.clear()
        lcd.message = "Enter input:\nKey B"
        key = None 
        while not key:
            user_input = input(f"Enter key B for sector {sector} (Enter 'b' for byte mode): ")
            if user_input.lower() == "b":
                key = BytesToByteArray(length=6)
            else:
                key = StringToByteArray(input_str=user_input, max_len=6)
        
        lcd.clear()
        lcd.message = "Enter input:\nNew Key A"
        new_key_a = None
        while not new_key_a:
            user_input = input("Enter new key A (Enter 'b' for byte mode): ")
            if user_input.lower() == "b":
                new_key_a = BytesToByteArray(length=6)
            else:
                new_key_a = StringToByteArray(input_str=user_input, max_len=6)
        
        lcd.clear()
        lcd.message = "Enter input:\nNew Key B"
        new_key_b = None
        while not new_key_b:
            user_input = input("Enter new key B (Enter 'b' for byte mode): ")
            if user_input.lower() == "b":
                new_key_b = BytesToByteArray(length=6)
            else:
                new_key_b = StringToByteArray(input_str=user_input, max_len=6)
                    
        lcd.clear()
        lcd.message = "Enter input:\nAccess Bits"
        access_bits = None
        while not access_bits:
            user_input = input(f"Use the recomended access bits {default_access_bits}? (Y/n): ")
            if user_input.lower() == "n":
                access_bits = BytesToByteArray(length=4)
            else:
                access_bits = bytearray(default_access_bits)
        
        CreateNewTrailer(scanner=nfc, sector=sector, key_b=key, new_key_a=new_key_a, new_key_b=new_key_b, access_bits=access_bits)
        
    elif action.lower() == "u":  # Get card UID option
        uid = GetCardUID(scanner=nfc)
        lcd.clear()
        lcd.message = f"Card found:\n" + f"{[i for i in uid]}".replace(" ", "")
        
    elif action.lower() == "q":  # Quit program
        running = False
        lcd.clear()
        lcd.message = "Press any button\nto quit..."
        
    else:
        toneFail()
        lcd.clear()
        lcd.message = "ERROR\nCheck console"
        print("ERROR: Invalid action.")
    
    # Wait for any button input before continue
    print("Press any button to continue...")
    wait_for_button_press()
    lcd.clear()
    lcd.backlight = False 
    
