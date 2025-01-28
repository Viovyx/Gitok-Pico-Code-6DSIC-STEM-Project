import board
import digitalio
import pwmio
import time
import adafruit_character_lcd.character_lcd as characterlcd

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

# == Controlling LCD ==
# Turn backlight on
lcd.backlight = True

# A smiley face character
smiley_face = [
    0b00000,  # Top row (all pixels off)
    0b00000,  # Second row (eyes)
    0b00000,  # Third row (eyes)
    0b00000,  # Fourth row (empty)
    0b00000,  # Fifth row (mouth corners)
    0b00000,  # Sixth row (mouth middle)
    0b00000,  # Seventh row (empty)
    0b00000   # Bottom row (all pixels off)
]

# Load the custom character into slot 0
lcd.create_char(0, smiley_face)

lcd.clear()
# lcd.message = "Hello :)\n"
# lcd.message += "\x00"  # Display the custom character from slot 0
lcd.message = "ERROR\nCheck console"