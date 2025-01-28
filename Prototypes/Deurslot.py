import board
import time
import digitalio
import pwmio

actuator = digitalio.DigitalInOut(board.GP15)
actuator.direction = digitalio.Direction.OUTPUT

actuator2 = digitalio.DigitalInOut(board.GP16)
actuator2.direction = digitalio.Direction.OUTPUT

buzzer = pwmio.PWMOut(board.GP14, variable_frequency=True)

reed = digitalio.DigitalInOut(board.GP22)
reed.direction = digitalio.Direction.INPUT

def Slot():
    ToneBuzz()
    actuator.value = True
    time.sleep(3)


def lamp():
    actuator2.value = True
    time.sleep(3)
    
def ToneBuzz():
    buzzer.duty_cycle = 2**14
    buzzer.frequency = 300
    

while True:
    print(reed.value)
    Slot()
    actuator.value = False
    buzzer.duty_cycle = 0
    print(reed.value)
    lamp()
    actuator2.value =False
    print(reed.value)
    Slot()
    lamp()
    print(reed.value)
    actuator.value = False
    actuator2.value = False
    buzzer.duty_cycle = 0
    time.sleep(3)
    