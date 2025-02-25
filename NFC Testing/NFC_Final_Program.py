import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
from adafruit_pn532.adafruit_pn532 import MIFARE_CMD_AUTH_A, MIFARE_CMD_AUTH_B

# -------------
# Functions
# -------------
def InitiateNFC(i2c_sda: Pin, i2c_scl: Pin):
    print("Initiating pn532...")
    i2c = busio.I2C(scl=i2c_scl, sda=i2c_sda)
    pn532 = PN532_I2C(i2c, debug=False)
    ic, ver, rev, support = pn532.firmware_version
    print(f"Found pn532 with firmware version: {ver}.{rev}")
    pn532.SAM_configuration()
    
    return pn532


def StringToByteArray(input_str: str, max_len: int):
    if len(input_str) > max_len:
        print(f"ERROR: Length is longer than the max ({max_len})! \n")
        return 
    data = [ord(char) for char in input_str]
    for i in range(max_len - len(data)):
        data.append(0)
    data_bytes = bytearray(data)
    
    return data_bytes


def BitsToByteArray(length: int):
    bits = []
    for i in range(length):
        bit = None
        while not bit:
            user_bit = input(f"Enter bit {i+1}: ")
            try:
                if 0 <= int(user_bit) <= 255:
                    bit = int(user_bit)
                else:
                    raise Exception()
            except:
                print("ERROR: Please enter an integer between 0-255.")
        bits.append(bit)
    bytes = bytearray(bits)

    return bytes


def GetCardUID(scanner: PN532_I2C):
    print("Waiting for card", end="")
    while True:
        uid = scanner.read_passive_target(timeout=0.5)
        print(".", end="")
        if uid is not None:
            break
    print(f"\nFound card with UID: {[i for i in uid]}")
    
    return uid
    

def AuthBlock(scanner: PN532_I2C, block: int, key: bytearray, b: bool = False):
    uid = GetCardUID(scanner=scanner)
    print(f"Authenticating block {block} ...")
    authenticated = scanner.mifare_classic_authenticate_block(uid, block, MIFARE_CMD_AUTH_B if b else MIFARE_CMD_AUTH_A, key)
    if authenticated:
        print("Authentication SUCCESFUL! \n")
    else:
        print("Authentication FAILED!")
        
    return authenticated 


def ReadBlock(scanner: PN532_I2C, block: int, key_a: bytearray):
    authenticated = AuthBlock(scanner=scanner, block=block, key=key_a)
    if authenticated:
        print(f"Reading block {block}...")
        try:
            value = [hex(x)[2:] for x in scanner.mifare_classic_read_block(block)]
            return value
        except:
            print("ERROR: Something went wrong while reading.")
            return False 


def WriteBlock(scanner: PN532_I2C, block: int, key_b: bytearray, data: bytearray):
    authenticated = AuthBlock(scanner=scanner, block=block, key=key_b, b=True)
    if authenticated:
        print(f"Writing data to block {block}...")
        try:
            scanner.mifare_classic_write_block(block, data)
            print(f"Wrote to block {block}")
            return True 
        except:
            print("ERROR: Something went wrong while writing the data.")
            return False 
            
            
def CreateNewTrailer(scanner: PN532_I2C, sector: int,  key_b: bytearray, new_key_a: bytearray, new_key_b: bytearray, access_bits: bytearray):
    trailer = new_key_a + access_bits + new_key_b
    block = 4*sector - 1
    authenticated = AuthBlock(scanner=scanner, block=block,  key=key_b, b=True)
    if authenticated:
        print(f"Writing new trailer for sector {sector}...")
        if WriteBlock(scanner=scanner, block=block, key_b=key_b, data=trailer):
            print("Key A\t Access Bits\t Key B")
            print(f"{new_key_a}\t {access_bits}\t {new_key_b}")


# -------------
# Program
# -------------
nfc_sda = board.GP14
nfc_scl = board.GP15
nfc = InitiateNFC(i2c_sda=nfc_sda, i2c_scl=nfc_scl)


while True:
    print("\n|--------------------------------------------------------------------------------|")
    print("| Actions: r = Reading, w = writing, t = change sector trailer, u = Get card uid |")
    print("|--------------------------------------------------------------------------------|\n")
    action = input("Enter action: ")

    if action.lower() == "r":  # Reading option
        block = None 
        while not block:
            user_input = input("Enter the block number: ")
            try:
                block = int(user_input)
            except:
                print("ERROR: Please enter an integer.")
        
        key = None 
        while not key:
            user_input = input(f"Enter key A for sector {int(block/4)+1} (Enter 'b' for bits mode): ")
            if user_input.lower() == "b":
                key = BitsToByteArray(length=6)
            else:
                key = StringToByteArray(input_str=user_input, max_len=6)
        
        data = ReadBlock(scanner=nfc, block=block, key_a=key)
        if data:
            print(f"Data (bytes in hex): {data}")
            try:
                print(f"Data (text): {bytearray.fromhex(''.join(data)+'0').decode() if len(''.join(data))%2 else bytearray.fromhex(''.join(data)).decode()}")
            except:
                print("Data (text): [ERROR Converting]")

    elif action.lower() == "w":  # Writing option
        block = None 
        while not block:
            user_input = input("Enter the block number: ")
            try:
                block = int(user_input)
            except:
                print("ERROR: Please enter an integer.")
        
        key = None 
        while not key:
            user_input = input(f"Enter key B for sector {int(block/4)+1} (Enter 'b' for bits mode): ")
            if user_input.lower() == "b":
                key = BitsToByteArray(length=6)
            else:
                key = StringToByteArray(input_str=user_input, max_len=6)
            
        data = None
        while not data:
            user_input = input("Enter the data to write to block {block}: ")
            data = StringToByteArray(input_str=user_input, max_len=16)
        
        WriteBlock(scanner=nfc, block=block, key_b=key, data=data)

    elif action.lower() == "t":  # Change sector trailer option
        sector = None
        while not sector:
            user_input = input("Enter the sector number: ")
            try:
                sector = int(user_input)
            except:
                print("ERROR: Please enter an integer.")
                      
        key = None 
        while not key:
            user_input = input(f"Enter key B for sector {sector} (Enter 'b' for bits mode): ")
            if user_input.lower() == "b":
                key = BitsToByteArray(length=6)
            else:
                key = StringToByteArray(input_str=user_input, max_len=6)
                      
        new_key_a = None
        while not new_key_a:
            user_input = input("Enter new key A (Enter 'b' for bits mode): ")
            if user_input.lower() == "b":
                new_key_a = BitsToByteArray(length=6)
            else:
                new_key_a = StringToByteArray(input_str=user_input, max_len=6)
        
        new_key_b = None
        while not new_key_b:
            user_input = input("Enter new key B (Enter 'b' for bits mode): ")
            if user_input.lower() == "b":
                new_key_b = BitsToByteArray(length=6)
            else:
                new_key_b = StringToByteArray(input_str=user_input, max_len=6)
                      
        access_bits = None
        while not access_bits:
            user_input = input("Use the recomended access bits [8,119,143,255]? (Y/n): ")
            if user_input.lower() == "n":
                access_bits = BitsToByteArray(length=4)
            else:
                access_bits = bytearray([8,119,143,255])
        
        CreateNewTrailer(scanner=nfc, sector=sector, key_b=key, new_key_a=new_key_a, new_key_b=new_key_b, access_bits=access_bits)
        
    elif action.lower() == "u":  # Get card UID option
        GetCardUID(scanner=nfc)
        
    else:
        print("ERROR: Invalid action.")
    
    input("\nPress ENTER to continue...")