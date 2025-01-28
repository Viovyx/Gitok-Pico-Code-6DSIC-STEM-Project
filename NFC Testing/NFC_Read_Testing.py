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

keyA = bytearray([68,101,118,75,101,121])

while True:
    # Check if a card is available to read
    uid = pn532.read_passive_target(timeout=0.5)
    print(".", end="")
    # Try again if no card is available.
    if uid is not None:
        break

print("")

print("Found card with UID:", [hex(i) for i in uid])

block = 2
print(f"Authenticating block {block} ...")

authenticated = pn532.mifare_classic_authenticate_block(uid, block, MIFARE_CMD_AUTH_A, keyA)
if not authenticated:
    print("Authentication failed!")

# Read block #6
read_hex = [hex(x)[2:] for x in pn532.mifare_classic_read_block(block)]
read_hex_str = ''.join(read_hex).upper()

print(
    f"Trying to read data from block {block}:\n",
    f"\bhex array: {read_hex}\n",
    f"\bhex string: {read_hex_str}",
)
