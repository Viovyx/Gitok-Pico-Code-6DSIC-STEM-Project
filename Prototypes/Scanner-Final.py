import board, time, json
import busio, pwmio, digitalio
import os, ssl, socketpool, wifi, math
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_character_lcd.character_lcd as characterlcd
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_A, MIFARE_CMD_AUTH_B

# -------------
# Functions
# -------------
# NFC functions
def InitiateNFC(i2c_sda: Pin, i2c_scl: Pin):
    print("Initiating pn532...")
    i2c = busio.I2C(scl=i2c_scl, sda=i2c_sda)
    pn532 = PN532_I2C(i2c, debug=False)
    ic, ver, rev, support = pn532.firmware_version
    print(f"Found pn532 with firmware version: {ver}.{rev}")
    pn532.SAM_configuration()
    
    return pn532


def GetCardUID(scanner: PN532_I2C):
    print("Waiting for card...")
    while True:
        uid = scanner.read_passive_target(timeout=0.5)
        if uid is not None:
            break
        mqtt_client.loop()
    print(f"\nFound card with UID: {[i for i in uid]}")
    
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


def ReadBlock(scanner: PN532_I2C, block: int, key_a: bytearray):
    authenticated = AuthBlock(scanner=scanner, block=block, key=key_a)
    if authenticated:
        print(f"Reading block {block}...")
        try:
            value = [hex(x)[2:] for x in scanner.mifare_classic_read_block(block)]
            return value
        except:
            print("ERROR: Something went wrong while reading.")
            return False 


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
            
            
def CreateNewTrailer(scanner: PN532_I2C, sector: int,  key_b: bytearray, new_key_a: bytearray, new_key_b: bytearray, access_bits: bytearray):
    trailer = new_key_a + access_bits + new_key_b
    block = 4*sector - 1
    authenticated = AuthBlock(scanner=scanner, block=block,  key=key_b, b=True)
    if authenticated:
        print(f"Writing new trailer for sector {sector}...")
        if WriteBlock(scanner=scanner, block=block, key_b=key_b, data=trailer):
            print("Key A\t Access Bits\t Key B")
            print(f"{new_key_a}\t {access_bits}\t {new_key_b}")
            return True
    else:
        return False
    

# Converters
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

# Other
def getCardPass(scanner):
    key_a =StringToByteArray(os.getenv("CARD_KEY_A"), max_len=6)
    pass_block = os.getenv("CARD_PASS_BLOCK")
    data = ReadBlock(scanner=scanner, block=pass_block, key_a=key_a)
    if data:
        card_pass = f"{bytearray.fromhex(''.join(data)+'0').decode() if len(''.join(data))%2 else bytearray.fromhex(''.join(data)).decode()}".replace("\x00","")
        print(f"[DEBUG] Card Pass: {card_pass}")
        return card_pass

def configureNewCard():
    lcd.clear()
    lcd.message = "Connect to PC\n& Follow Steps!"

    print("\nConfiguring new card. Follow the steps precisely!")
    print("-----------------------------------------------------\n")

    block = os.getenv("CARD_PASS_BLOCK")
    sector = math.floor(block/4)+1

    key_b = None
    while not key_b:
        user_input = input("[1] Enter Admin Key (key_b): ")
        key_b = StringToByteArray(user_input, max_len=6)
    
    user_input = input("[2] Should the current admin key on this card be updated? This should be run if this is a completely new card! (y/N): ")
    if user_input.lower() == "y":
        key_a = StringToByteArray(os.getenv("CARD_KEY_A"), max_len=6)
        bits = bytearray(list(map(int, (os.getenv("CARD_BITS")).split(","))))
        
        prev_key_b = None
        while not prev_key_b:
            user_input = input("[2.1] Enter current key_b (Press enter for factory default or enter 'b' for bits mode): ")
            if len(user_input):
                if user_input.lower() == "b":
                    prev_key_b = BitsToByteArray(length=6)
                else:
                    prev_key_b = StringToByteArray(user_input, max_len=6)
            else:
                prev_key_b = bytearray([255,255,255,255])

        lcd.clear()
        lcd.message = "Creating Trailer\nPlease wait..."
        if not CreateNewTrailer(scanner=nfc, sector=sector, key_b=prev_key_b, new_key_a=key_a, new_key_b=key_b, access_bits=bits):
            lcd.clear()
            lcd.message = "Trailer Creation\nFailed!"
            toneFail()
            time.sleep(1)
            return False

    card_pass = None
    while not card_pass:
        user_input = input("[3] Enter a card pass. This will be used to identify the card: ")
        card_pass = StringToByteArray(user_input, max_len=16)

    lcd.clear()
    lcd.message = "Creating Card\nPlease wait..."
    uid = GetCardUID(scanner=nfc)
    card_uid = card_uid = f"{[i for i in uid]}".replace(" ", "")
    if WriteBlock(scanner=nfc, block=block, key_b=key_b, data=card_pass):
        lcd.clear()
        lcd.message = "Card Creation\nSuccessful!"
        toneSuccess()
        card_pass = getCardPass(scanner=nfc)
        return {"uid":card_uid, "pass":card_pass}
    else:
        lcd.clear()
        lcd.message = "Card Creation\nFailed!"
        toneFail()
        time.sleep(1)
        return False

# Button + lcd nav funtions
def wait_for_button_press():
    while True:        
        if button_up.value or button_down.value or button_confirm.value:
            time.sleep(0.1)
            if button_up.value:
                toneSuccess()
                return "up"
            if button_down.value:
                toneSuccess()
                return "down"
            if button_confirm.value:
                toneSuccess()
                return "confirm"

def navigate_options(options):
    index = 0
    while True:
        lcd.clear()
        lcd.message = "Select Action:\n"
        lcd.message += options[index]
        action = wait_for_button_press()
        if action == "up":
            index = (index - 1) % len(options)
        elif action == "down":
            index = (index + 1) % len(options)
        elif action == "confirm":
            lcd.clear()
            return index
        

# ---------------
# Network + MQTT
# ---------------

# MQTT Functions
waiting_for_action = False  
def wait_for_action():
    global waiting_for_action
    waiting_for_action = True
    print("[DEBUG] Waiting for MQTT action...")

    while waiting_for_action:
        mqtt_client.loop()
        
def subscribe_to(topics: []):
    for topic in topics:
        topic = aio_user + "/feeds/scanner." + topic
        mqtt_client.subscribe(topic, 1)

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
    global waiting_for_action
    print(f"[MQTT] New message on topic {topic}: {message}")

    if topic == aio_user + "/feeds/scanner.action" and waiting_for_action:
        data = json.loads(message)  # {"user":1, "action":1, "door_ip":"192.168.0.11"}
        action_id = data["action"]
        action = ["failed", "successful", "checkout"][action_id]
        
        if action == "failed":  # not allowed
            print("[DEBUG] Access not allowed")
            toneFail()
            lcd.clear()
            lcd.message = "ERROR\nNo access!"
            
        elif action == "successful":  # allowed => open door
            print("[DEBUG] Access allowed => opening door")
            toneSuccess()
            lcd.clear()
            lcd.message = "Opening Door...\nPlease wait"
            
        elif action == "checkout":  # check out
            print("[DEBUG] User checked out")
            toneSuccess()
            lcd.clear()
            lcd.message = "Checking out...\nPlease wait"
            
        else:  # invalid action
            print("[DEBUG] Invalid action")
            lcd.clear()
            lcd.message = "ERROR\nTry again"
            toneFail()
        
        waiting_for_action = False

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

# Setup topics to subscribe to here
topics = ["action"]
subscribe_to(topics)

# -------------
# Pin Setup
# -------------
# NFC Setup
nfc_sda = board.GP14
nfc_scl = board.GP15
nfc = InitiateNFC(i2c_sda=nfc_sda, i2c_scl=nfc_scl)

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
runnning = True

check_card_feed = aio_user + "/feeds/scanner.checkcard"
action_feed = aio_user + "/feeds/scanner.action"
ip = str(wifi.radio.ipv4_address)
key_a = StringToByteArray(os.getenv("CARD_KEY_A"), max_len=6)
pass_block=os.getenv("CARD_PASS_BLOCK")
options = ["Start Scanner", "Card Info", ip]  # "Create Card" option removed

while runnning:
    choice = options[navigate_options(options)]

    if choice == "Start Scanner":
        while runnning:
            lcd.clear()
            lcd.message = "Scan Your\nAccess Card"
            
            uid = GetCardUID(scanner=nfc)
            card_uid = f"{[i for i in uid]}".replace(" ", "")
            card_pass = getCardPass(scanner=nfc)
            
            if card_pass:
                print(f"[DEBUG] Found card_pass for {card_uid}: {card_pass}")
                mqtt_client.publish(check_card_feed, str({"uid":card_uid.replace(",", "."), "pass":card_pass, "ip":ip}).replace("'", '"'))
            
                lcd.clear()
                lcd.message = "Loading...\nPlease wait"
                wait_for_action()
                time.sleep(2)
            else:
                print("[ERROR] No Pass Found!")
                mqtt_client.publish(action_feed, str({"user":0,"action":0,"door_ip":0}).replace("'", '"'))
                lcd.clear()
                lcd.message = f"ERROR\nTry again"
                toneFail()
                time.sleep(0.5)
    elif choice == "Create Card":
        card = configureNewCard()
        card_pass = getCardPass(scanner=nfc)
        if card and card_pass == card["pass"]:
            lcd.clear()
            lcd.message = f"{card["uid"]}\n{card["pass"]}"
            
            print("[DEBUG] New card created succesfully!")
            print("[INFO] Go to the web panel and create a new keycard with following info:")
            print(f"CardUID: {card["uid"]}")
            print(f"UniquePass: {card["pass"]}")
            time.sleep(2)
        else:
            toneFail()
            print("[DEBUG] New card creation failed! Password was not set correctly.")
            lcd.clear()
            lcd.message = "Failed to\nSet Pass!"
    elif choice == "Card Info":
        lcd.clear()
        lcd.message = "Connect to PC\n& Enter Key!"
        
        key_b = None
        while not key_b:
            user_input = input("Enter Admin key (key_b): ")
            key_b = StringToByteArray(user_input, max_len=6)
        
        lcd.clear()
        lcd.message = "Scan Your\nAccess Card"
        if AuthBlock(scanner=nfc, block=pass_block, key=key_b, b=True):
            lcd.clear()
            lcd.message = "Auth Success!"
            toneSuccess()

            uid = GetCardUID(scanner=nfc)
            card_uid = f"{[i for i in uid]}".replace(" ", "").replace("[", "").replace("]", "")
            card_pass = getCardPass(scanner=nfc)

            if card_pass:
                lcd.clear()
                lcd.message = f"{card_uid}\n{card_pass}"
                print("[DEBUG] Card info read succesfully!")
                print("[INFO] Go to the web panel and create a new keycard with following info:")
                print(f"CardUID: [{card_uid}]")
                print(f"UniquePass: {card_pass}")
                time.sleep(2)
            else:
                lcd.clear()
                lcd.message = "Reading Failed!"
                toneFail()
        else:
            lcd.clear()
            lcd.message = "Auth Failed!"
            toneFail()
