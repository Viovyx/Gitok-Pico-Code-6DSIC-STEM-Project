import board, time, digitalio, pwmio
import os, ssl, socketpool, wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import asyncio, random
# Connect to WiFi
print("Connecting to WiFi")
wifi.radio.connect(os.getenv("WIFI_SSID2"), os.getenv("WIFI_PASSWORD2"))
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
actuator = digitalio.DigitalInOut(board.GP15)
actuator.direction = digitalio.Direction.OUTPUT
actuator.value = False

actuator2 = digitalio.DigitalInOut(board.GP16)
actuator2.direction = digitalio.Direction.OUTPUT
actuator2.value = False

buzzer = pwmio.PWMOut(board.GP14, variable_frequency=True)

reed = digitalio.DigitalInOut(board.GP22)
reed.direction = digitalio.Direction.INPUT
print("succes")
#===============================================================
async def ToneBuzz():
    buzzer.duty_cycle = 2**14
    buzzer.frequency = 300
    
async def OpenDoor():
    actuator.value = True
    actuator2.value = True
    await ToneBuzz()
    await asyncio.sleep(6)
    actuator.value = False
    actuator2.value = False
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
    if message == "1":
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
    while True:
        val = random.randint(0,1)
        mqtt_client.publish(mqtt_topic,val)
        await asyncio.sleep(interval)

async def ListenMQTTRequest(interval):
    while True:
        mqtt_client.loop()
        try:
            mqtt_client.message
        except:
            print("no messages")
            await asyncio.sleep(interval)
        
async def main():
    Reed_task = asyncio.create_task(ListenReed(2))
    MQTT_task = asyncio.create_task(ListenMQTTRequest(2))
    await asyncio.gather(Reed_task,MQTT_task)

asyncio.run(main())
