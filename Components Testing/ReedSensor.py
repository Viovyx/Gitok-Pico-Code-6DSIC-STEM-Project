import time
import digitalio
import board

reed = digitalio.DigitalInOut(board.GP0)
reed.direction = digitalio.Direction.INPUT

prevVal = None
while True:
    val = reed.value
    if prevVal != val:
        if val == True:
            print(0)
            
        else:
            print(1)
    prevVal = val
    time.sleep(1)
