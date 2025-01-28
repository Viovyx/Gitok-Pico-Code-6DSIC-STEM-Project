text = b"DevKey"

text_hex = text.hex()
text_hexstr = bytearray.fromhex(text_hex)
    
print(text_hex)
print(text_hexstr)

data = bytearray([68,101,118,75,101,121,127,7,136,255,255,255,255,255,255])

print(len(data))
assert (
            data is not None and len(data) == 16
        ), "Data must be an array of 16 bytes!"

print(type(b"\x44\x65\x76\x4B\x65\x79"))