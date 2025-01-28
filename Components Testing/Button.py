import time
import digitalio
import board

button1 = digitalio.DigitalInOut(board.GP10)
button1.direction = digitalio.Direction.INPUT
button1.pull = digitalio.Pull.UP

button2 = digitalio.DigitalInOut(board.GP11)
button2.direction = digitalio.Direction.INPUT
button2.pull = digitalio.Pull.UP

button3 = digitalio.DigitalInOut(board.GP12)
button3.direction = digitalio.Direction.INPUT
button3.pull = digitalio.Pull.UP

led1 = digitalio.DigitalInOut(board.GP3)
led1.direction = digitalio.Direction.OUTPUT

led2 = digitalio.DigitalInOut(board.GP4)
led2.direction = digitalio.Direction.OUTPUT

led3 = digitalio.DigitalInOut(board.GP5)
led3.direction = digitalio.Direction.OUTPUT

prevButton1 = button1.value
prevButton2 = button2.value
prevButton3 = button3.value

while True:
    
    prevButton1 = button1.value
    prevButton2 = button2.value
    prevButton3 = button3.value
    
    if button1.value or button2.value or button3.value :
        print(f"{button1.value}		{button2.value}		{button3.value}")
        time.sleep(0.02)
        
        if button1.value and not prevButton1:
            led1.value = True
            time.sleep(0.3)
            
        elif  button2.value and not prevButton2:
            led2.value = True
            time.sleep(0.3)
            
        elif button3.value and not prevButton3:
            led3.value = True
            time.sleep(0.3)
    
    led1.value = False
    led2.value = False
    led3.value = False
