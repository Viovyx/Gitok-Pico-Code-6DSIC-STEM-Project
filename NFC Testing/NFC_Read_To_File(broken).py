import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_A

# I2C connection:
i2c_sda = board.GP4
i2c_scl = board.GP5
i2c = busio.I2C(i2c_scl, i2c_sda)

# Setup PN532
pn532 = PN532_I2C(i2c, debug=False)
ic, ver, rev, support = pn532.firmware_version
print("Found PN532 with firmware version: {0}.{1}".format(ver, rev))

# Configure PN532 to communicate with MiFare cards
pn532.SAM_configuration()


print("Waiting for RFID/NFC card to read from!")

keyA = b"\xFF\xFF\xFF\xFF\xFF\xFF"

uids = []
try:
    with open('uids.txt', 'r') as file:
        for line in file.readlines():
            uids.append(line.strip())
    for line in uids:
        print(line)
except:
    pass  

while True:
    # Check if a card is available to read
    uid = pn532.read_passive_target(timeout=0.5)
    # Try again if no card is available.
    if uid and uid not in uids:
        read_hex = [hex(x)[2:] for x in uid]
        print(f"Found card with UID: {read_hex}")
        uids.append(read_hex)
        with open('uids.txt', 'w+') as file:
            file.write(f'{read_hex}')