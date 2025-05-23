import board, time, digitalio, pwmio
import os, ssl, socketpool, wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import asyncio, random
# Connect to WiFi
print("Connecting to WiFi")
print(os.getenv("WIFI_SSID"))
wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASS"))
print("Connected!")

# Create socketpool
print("creating socketpool")
pool = socketpool.SocketPool(wifi.radio)
print("socketpool created")

# Get adafruit io username and key from settings.toml
print("logging into adafruitIO")

aio_user = os.getenv("AIO_USER")
aio_key = os.getenv("AIO_KEY")

print("logged in")


mqtt_topic = aio_user+"/feeds/lock.status"

#Initializing pins
#=============================================================
print("initializing pins")
led = digitalio.DigitalInOut(board.GP18)
led.direction = digitalio.Direction.OUTPUT
led.value = False

slot = digitalio.DigitalInOut(board.GP22)
slot.direction = digitalio.Direction.OUTPUT
slot.value = False

buzzer = pwmio.PWMOut(board.GP16, variable_frequency=True)

reed = digitalio.DigitalInOut(board.GP28)
reed.direction = digitalio.Direction.INPUT
print("succes")
#===============================================================
def ToneBuzz():
    buzzer.duty_cycle = 2**14
    buzzer.frequency = 300
    time.sleep(4)
    buzzer.duty_cycle = 0
    
async def OpenDoor():
    led.value = True
    slot.value = True
    ToneBuzz()
    led.value = False
    slot.value = False
    print("done")
    
# Define callback methods which are called when events occur
#===========================================================
def connect(mqtt_client, userdata, flags, rc):
    # This function will be called when the mqtt_client is connected
    # successfully to the broker.
    print("Connected to MQTT Broker!")
    print(f"Flags: {flags}\n RC: {rc}")


def disconnect(mqtt_client, userdata, rc):
    # This method is called when the mqtt_client disconnects
    # from the broker.
    print("Disconnected from MQTT Broker!")


def subscribe(mqtt_client, userdata, topic, granted_qos):
    # This method is called when the mqtt_client subscribes to a new feed.
    print(f"Subscribed to {topic} with QOS level {granted_qos}")


def unsubscribe(mqtt_client, userdata, topic, pid):
    # This method is called when the mqtt_client unsubscribes from a feed.
    print(f"Unsubscribed from {topic} with PID {pid}")


def publish(mqtt_client, userdata, topic, pid):
    # This method is called when the mqtt_client publishes data to a feed.
    print(f"Published to {topic} with PID {pid}")


def message(client, topic, message):
    print(str(wifi.radio.ipv4_address))
    if message == str(wifi.radio.ipv4_address):
        asyncio.create_task(OpenDoor())
        print("open")
        
#===========================================================
        
mqtt_client = MQTT.MQTT(
    broker=os.getenv("BROKER"),
    username=aio_user,
    password=aio_key,
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Connect callback handlers to mqtt_client
mqtt_client.on_connect = connect
mqtt_client.on_subscribe = subscribe
mqtt_client.on_unsubscribe = unsubscribe
mqtt_client.on_publish = publish
mqtt_client.on_message = message
mqtt_client.on_disconnect = disconnect

print("Attempting to connect to %s" % mqtt_client.broker)
mqtt_client.connect()  

# Define callback methods which are called when events occur

        
# MQTT Functions
def subscribe_to(topics: []):
    for topic in topics:
        topic = aio_user + "/feeds/lock." + topic
        mqtt_client.subscribe(topic,1)

# Setup topics to subscribe to here
topics = ["open"]
subscribe_to(topics)

async def ListenReed(interval):
    prevVal = None
    status = 0
    ip = str(wifi.radio.ipv4_address)
    
    status = 2 if reed.value == True else 1
    mqtt_client.publish(mqtt_topic,str({"door_ip": ip, "status": status}).replace("'",'"'))
    
    while True:
        val = reed.value
        if prevVal != val:
            status = 2 if val == True else 1
            mqtt_client.publish(mqtt_topic,str({"door_ip": ip, "status": status}).replace("'",'"'))
    
        prevVal = val
        await asyncio.sleep(interval)

async def ListenMQTTRequest(interval):
    while True:
        mqtt_client.loop()
        await asyncio.sleep(interval)
        
async def main():
    Reed_task = asyncio.create_task(ListenReed(1))
    MQTT_task = asyncio.create_task(ListenMQTTRequest(0.01))
    await asyncio.gather(Reed_task,MQTT_task)

asyncio.run(main())
