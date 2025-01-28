import time
import digitalio
import board



reed = digitalio.DigitalInOut(board.GP0)
reed.direction = digitalio.Direction.INPUT
reed.pull = digitalio.Pull.UP

while True:
    
    print(reed.value)
            
    time.sleep(0.1)
