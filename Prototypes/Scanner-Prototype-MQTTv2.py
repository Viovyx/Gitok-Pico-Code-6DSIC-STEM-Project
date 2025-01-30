import board, time
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
        if message == "0":  # not allowed
            print("[DEBUG] Access not allowed")
            toneFail()
            lcd.clear()
            lcd.message = "ERROR\nNo access!"
            
        elif  message == "1":  # allowed => open door
            print("[DEBUG] Access allowed => opening door")
            toneSuccess()
            lcd.clear()
            lcd.message = "Opening Door..."
            open_door = aio_user + "/feeds/lock.open"
            mqtt_client.publish(open_door, 1)
            
        elif message == "2":  # check out
            print("[DEBUG] User checked out")
            toneSuccess()
            lcd.clear()
            lcd.message = "Checking out..."
            # No check out logic yet
            
        else:  # invalid action
            print("[DEBUG] Invalid action")
            toneFail()
            lcd.clear()
            lcd.message = "ERROR\nTry again"
        
        waiting_for_action = False

# ---------------
# Network + MQTT
# ---------------

# Connect to WiFi
print("[WIFI] Connecting to WiFi")
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
    "Open Door",
    "Get Card UID",
    "Quit Program"
]

lcd.backlight = True
runnning = True
while runnning:
    option = navigate_options(options)
    
    if option == 0:  # Open Door
        uid = GetCardUID(scanner=nfc)
        check_card = aio_user + "/feeds/scanner.checkcard"
        mqtt_client.publish(check_card, f"{[i for i in uid]}".replace(" ", ""))
        
        lcd.clear()
        lcd.message = "Waiting for\nresponse..."
        wait_for_action()
        time.sleep(2)
        
    elif option == 1:  # Get Card UID
        uid = GetCardUID(scanner=nfc)
        lcd.clear()
        lcd.message = f"Card found:\n" + f"{[i for i in uid]}".replace(" ", "").replace("[", "").replace("]", "")
        time.sleep(2)
        
    elif option == 2:  # Quit Program
        running = False
        lcd.backlight = False 
        mqtt_client.disconnect()
        break
        
    else:
        toneFail()
        lcd.clear()
        lcd.message = "ERROR\nCheck console"
        print("ERROR: Invalid action.")
        time.sleep(2)
    
    lcd.clear()