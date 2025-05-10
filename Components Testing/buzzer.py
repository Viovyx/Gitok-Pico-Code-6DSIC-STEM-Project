import time
import board
import pwmio


buzzer = pwmio.PWMOut(board.GP0, variable_frequency=True)
buzzer.duty_cycle = 2**15

def toneSucces():
    
    buzzer.duty_cycle=2**15
    buzzer.frequency = 850
    time.sleep(0.06) 
    buzzer.duty_cycle=0
    time.sleep(0.06)
    
def toneFail():
    
    buzzer.duty_cycle=2**15
    buzzer.frequency = 300
    time.sleep(1)
    buzzer.duty_cycle=0

def ToneBuzz():
    buzzer.duty_cycle = 2**14
    buzzer.frequency = 300
    time.sleep(4)
    buzzer.duty_cycle = 0

ToneBuzz()

time.sleep(1)

toneSucces()

time.sleep(1)

toneFail()