import board, time, asyncio, busio, pwmio, digitalio, os, ssl, socketpool, wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_character_lcd.character_lcd as characterlcd
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_A, MIFARE_CMD_AUTH_B

# ----------------
# Utility Functions
# ----------------

# (These functions still use time.sleep because they’re very short.
#  If you prefer to “asyncify” them, replace time.sleep with await asyncio.sleep.)

def toneSuccess():
    buzzer.duty_cycle = 2**15
    buzzer.frequency = 850
    time.sleep(0.06)
    buzzer.duty_cycle = 0
    time.sleep(0.06)

def toneFail():
    buzzer.duty_cycle = 2**15
    buzzer.frequency = 300
    time.sleep(0.3)
    buzzer.duty_cycle = 0

# ----------------
# NFC Functions
# ----------------

def InitiateNFC(i2c_sda, i2c_scl):
    print("Initiating PN532...")
    i2c = busio.I2C(scl=i2c_scl, sda=i2c_sda)
    pn532 = PN532_I2C(i2c, debug=False)
    ic, ver, rev, support = pn532.firmware_version
    print(f"Found PN532 with firmware version: {ver}.{rev}")
    pn532.SAM_configuration()
    return pn532

async def GetCardUID(scanner: PN532_I2C):
    lcd.clear()
    lcd.message = "Waiting for card"
    print("Waiting for card")
    while True:
        uid = scanner.read_passive_target(timeout=0.5)
        if uid is not None:
            break
        await asyncio.sleep(0)  # yield control
    print(f"Found card with UID: {[i for i in uid]}")
    return uid

# ----------------
# Button and LCD Navigation
# ----------------

async def wait_for_button_press():
    while True:
        # Check buttons – if any is pressed, wait a brief moment and then decide
        if button_up.value or button_down.value or button_confirm.value:
            await asyncio.sleep(0.1)
            if button_up.value:
                toneSuccess()
                return "up"
            if button_down.value:
                toneSuccess()
                return "down"
            if button_confirm.value:
                toneSuccess()
                return "confirm"
        await asyncio.sleep(0)  # yield control

async def navigate_options(options):
    index = 0
    while True:
        lcd.clear()
        lcd.message = "Select Action:\n" + options[index]
        action = await wait_for_button_press()
        if action == "up":
            index = (index - 1) % len(options)
        elif action == "down":
            index = (index + 1) % len(options)
        elif action == "confirm":
            lcd.clear()
            return index
        await asyncio.sleep(0)  # yield control

# ----------------
# MQTT Functions
# ----------------

waiting_for_action = False

async def wait_for_action():
    global waiting_for_action
    waiting_for_action = True
    print("[DEBUG] Waiting for MQTT action...")
    # Instead of calling mqtt_client.loop() here,
    # the separate keep-alive task will process MQTT events.
    while waiting_for_action:
        await asyncio.sleep(0.01)

def subscribe_to(topics: list):
    for topic in topics:
        t = aio_user + "/feeds/scanner." + topic
        mqtt_client.subscribe(t, 1)

# Callback functions (called synchronously by the MQTT library)
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

def message(client, topic, msg):
    global waiting_for_action
    print(f"[MQTT] New message on topic {topic}: {msg}")
    if topic == aio_user + "/feeds/scanner.action" and waiting_for_action:
        if msg == "0":  # not allowed
            print("[DEBUG] Access not allowed")
            toneFail()
            lcd.clear()
            lcd.message = "ERROR\nNo access!"
        elif msg == "1":  # allowed → open door
            print("[DEBUG] Access allowed → opening door")
            toneSuccess()
            lcd.clear()
            lcd.message = "Opening Door..."
            open_door = aio_user + "/feeds/lock.open"
            mqtt_client.publish(open_door, 1)
        elif msg == "2":  # check out
            print("[DEBUG] User checked out")
            toneSuccess()
            lcd.clear()
            lcd.message = "Checking out..."
        else:  # invalid action
            print("[DEBUG] Invalid action")
            toneFail()
            lcd.clear()
            lcd.message = "ERROR\nTry again"
        waiting_for_action = False

# ----------------
# Network and MQTT Setup
# ----------------

print(f"[WIFI] Connecting to WiFi ({os.getenv('WIFI_SSID')})")
wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASS"))
print("[WIFI] Connected!")

pool = socketpool.SocketPool(wifi.radio)

aio_user = os.getenv("AIO_USER")
aio_key = os.getenv("AIO_KEY")
aio_broker = os.getenv("BROKER")
aio_port = os.getenv("PORT")

mqtt_client = MQTT.MQTT(
    broker=aio_broker,
    username=aio_user,
    password=aio_key,
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

mqtt_client.on_connect = connect
mqtt_client.on_disconnect = disconnect
mqtt_client.on_subscribe = subscribe
mqtt_client.on_unsubscribe = unsubscribe
mqtt_client.on_publish = publish
mqtt_client.on_message = message

print(f"[MQTT] Attempting to connect to {mqtt_client.broker}")
mqtt_client.connect()

topics = ["action"]
subscribe_to(topics)

# ----------------
# Pin Setup
# ----------------

# NFC Setup
nfc_sda = board.GP14
nfc_scl = board.GP15
nfc = InitiateNFC(i2c_sda=nfc_sda, i2c_scl=nfc_scl)
default_access_bits = [8, 119, 143, 255]

# LCD Setup
lcd_rs = digitalio.DigitalInOut(board.GP0)
lcd_en = digitalio.DigitalInOut(board.GP1)
lcd_d4 = digitalio.DigitalInOut(board.GP2)
lcd_d5 = digitalio.DigitalInOut(board.GP3)
lcd_d6 = digitalio.DigitalInOut(board.GP4)
lcd_d7 = digitalio.DigitalInOut(board.GP5)
lcd_backlight = digitalio.DigitalInOut(board.GP6)

contrast = pwmio.PWMOut(board.GP7, frequency=5000, duty_cycle=0)
contrast_percentage = 60
contrast.duty_cycle = int(65535 * (1 - contrast_percentage/100))
lcd_columns = 16
lcd_rows = 2
lcd = characterlcd.Character_LCD_Mono(
    lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows, lcd_backlight
)

# Button Setup
button_up = DigitalInOut(board.GP10)
button_down = DigitalInOut(board.GP11)
button_confirm = DigitalInOut(board.GP12)

button_up.switch_to_input(pull=digitalio.Pull.DOWN)
button_down.switch_to_input(pull=digitalio.Pull.DOWN)
button_confirm.switch_to_input(pull=digitalio.Pull.DOWN)

# Buzzer Setup
buzzer = pwmio.PWMOut(board.GP13, variable_frequency=True)

# ----------------
# Async Tasks
# ----------------

async def mqtt_keep_alive():
    """Continuously call mqtt_client.loop() to process incoming/outgoing MQTT messages."""
    while True:
        mqtt_client.loop()
        await asyncio.sleep(0.01)

async def main():
    # Start the MQTT keep-alive task
    asyncio.create_task(mqtt_keep_alive())

    toneSuccess()  # initial tone to signal startup
    options = ["Open Door", "Get Card UID", "Quit Program"]
    lcd.backlight = True
    running = True

    while running:
        option = await navigate_options(options)
        if option == 0:  # Open Door
            uid = await GetCardUID(nfc)
            check_card = aio_user + "/feeds/scanner.checkcard"
            # Publish card UID (formatted as you did)
            mqtt_client.publish(check_card, f"{[i for i in uid]}".replace(" ", ""))
            lcd.clear()
            lcd.message = "Waiting for\nresponse..."
            await wait_for_action()
            await asyncio.sleep(2)

        elif option == 1:  # Get Card UID
            uid = await GetCardUID(nfc)
            lcd.clear()
            lcd.message = "Card found:\n" + f"{[i for i in uid]}".replace(" ", "").replace("[", "").replace("]", "")
            await asyncio.sleep(2)

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
            await asyncio.sleep(2)
        lcd.clear()

# Run the asyncio event loop
asyncio.run(main())
