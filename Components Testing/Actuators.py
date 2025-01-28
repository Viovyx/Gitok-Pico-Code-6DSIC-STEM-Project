import board
import time
import digitalio

actuator = digitalio.DigitalInOut(board.GP16)
actuator.direction = digitalio.Direction.OUTPUT

actuator2 = digitalio.DigitalInOut(board.GP15)
actuator2.direction = digitalio.Direction.OUTPUT

while True:
    actuator.value = True
    actuator2.value = False
    print("1")
    time.sleep(5)
    actuator.value = False
    actuator2.value = True
    print("2")
    time.sleep(5)
    actuator.value = True
    print("3")
    time.sleep(5)