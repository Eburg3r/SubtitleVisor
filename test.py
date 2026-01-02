# from machine import Pin, I2C
# from time import sleep_ms

# # -----------------------------
# # CONFIG
# # -----------------------------
# SDA_PIN = 4
# SCL_PIN = 5
# I2C_ID = 0
# I2C_FREQ = 100000
# LED_INDEX = 116      # <<< CHANGE THIS (0–143)
# BRIGHTNESS = 255

# ADDRS = (0x74, 0x77)

# # -----------------------------
# # I2C BUS RESET
# # -----------------------------
# def i2c_bus_reset():
#     sda = Pin(SDA_PIN, Pin.IN, Pin.PULL_UP)
#     scl = Pin(SCL_PIN, Pin.OUT)
#     scl.value(1)
#     sleep_ms(2)

#     # clock out any stuck bits
#     for _ in range(18):
#         scl.value(0)
#         sleep_ms(1)
#         scl.value(1)
#         sleep_ms(1)

#     # STOP condition
#     sda_out = Pin(SDA_PIN, Pin.OUT)
#     sda_out.value(0)
#     sleep_ms(1)
#     scl.value(1)
#     sleep_ms(1)
#     sda_out.value(1)
#     sleep_ms(1)

#     Pin(SDA_PIN, Pin.IN, Pin.PULL_UP)
#     Pin(SCL_PIN, Pin.IN, Pin.PULL_UP)

# # -----------------------------
# # IS31 HELPERS
# # -----------------------------
# def find_is31(i2c):
#     devs = i2c.scan()
#     for a in ADDRS:
#         if a in devs:
#             return a
#     return None

# def w(i2c, addr, reg, val):
#     i2c.writeto(addr, bytes([reg & 0xFF, val & 0xFF]))

# def bank(i2c, addr, b):
#     i2c.writeto(addr, bytes([0xFD, b & 0xFF]))
#     sleep_ms(1)

# def init_is31(i2c, addr):
#     # Function bank
#     bank(i2c, addr, 0x0B)
#     w(i2c, addr, 0x0A, 0x00)   # shutdown
#     sleep_ms(10)

#     # Frame 0
#     bank(i2c, addr, 0x00)

#     # Enable all LED control bits
#     for r in range(0x00, 0x12):
#         w(i2c, addr, r, 0xFF)

#     # Clear all PWM
#     for r in range(0x24, 0xB4):
#         w(i2c, addr, r, 0x00)

#     # Wake + picture mode
#     bank(i2c, addr, 0x0B)
#     w(i2c, addr, 0x00, 0x00)   # picture mode
#     w(i2c, addr, 0x01, 0x00)   # display frame 0
#     w(i2c, addr, 0x0A, 0x01)   # normal operation
#     sleep_ms(10)

# def set_led(i2c, addr, idx, pwm):
#     if not 0 <= idx < 144:
#         return
#     bank(i2c, addr, 0x00)
#     w(i2c, addr, 0x24 + idx, pwm)

# # -----------------------------
# # MAIN
# # -----------------------------
# print("Resetting I2C bus...")
# i2c_bus_reset()

# print("Creating I2C...")
# i2c = I2C(I2C_ID, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=I2C_FREQ)

# addr = find_is31(i2c)
# if addr is None:
#     print("ERROR: IS31FL3731 not found")
#     print("Scan:", i2c.scan())
# else:
#     print("Found IS31 at", hex(addr))
#     init_is31(i2c, addr)

#     print("Lighting LED index", LED_INDEX)
#     set_led(i2c, addr, LED_INDEX, BRIGHTNESS)

#     print("Done. LED should remain ON.")


# from machine import Pin, I2C
# from time import sleep_ms

# SDA_PIN = 4
# SCL_PIN = 5
# I2C_ID = 0
# FREQ = 100000

# ADDRS = (0x74, 0x77)

# def i2c_bus_reset():
#     sda = Pin(SDA_PIN, Pin.IN, Pin.PULL_UP)
#     scl = Pin(SCL_PIN, Pin.OUT)
#     scl.value(1)
#     sleep_ms(2)

#     for _ in range(18):
#         scl.value(0); sleep_ms(1)
#         scl.value(1); sleep_ms(1)

#     sda_out = Pin(SDA_PIN, Pin.OUT)
#     sda_out.value(0); sleep_ms(1)
#     scl.value(1); sleep_ms(1)
#     sda_out.value(1); sleep_ms(1)

#     Pin(SDA_PIN, Pin.IN, Pin.PULL_UP)
#     Pin(SCL_PIN, Pin.IN, Pin.PULL_UP)

# def make_i2c():
#     return I2C(I2C_ID, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=FREQ)

# def find_addr(i2c):
#     devs = i2c.scan()
#     for a in ADDRS:
#         if a in devs:
#             return a, devs
#     return None, devs

# def w(i2c, addr, reg, val):
#     i2c.writeto(addr, bytes([reg & 0xFF, val & 0xFF]))

# def bank(i2c, addr, b):
#     i2c.writeto(addr, bytes([0xFD, b & 0xFF]))
#     sleep_ms(1)

# def init_is31(i2c, addr):
#     bank(i2c, addr, 0x0B)
#     w(i2c, addr, 0x0A, 0x00)  # shutdown
#     sleep_ms(10)

#     bank(i2c, addr, 0x00)
#     for r in range(0x00, 0x12):
#         w(i2c, addr, r, 0xFF)

#     for r in range(0x24, 0xB4):
#         w(i2c, addr, r, 0x00)

#     bank(i2c, addr, 0x0B)
#     w(i2c, addr, 0x00, 0x00)  # picture mode
#     w(i2c, addr, 0x01, 0x00)  # display frame 0
#     w(i2c, addr, 0x0A, 0x01)  # normal op
#     sleep_ms(10)

# def clear_all(i2c, addr):
#     bank(i2c, addr, 0x00)
#     for r in range(0x24, 0xB4):
#         w(i2c, addr, r, 0x00)

# def set_idx(i2c, addr, idx, pwm):
#     bank(i2c, addr, 0x00)
#     w(i2c, addr, 0x24 + idx, pwm)

# def main():
#     print("\nResetting I2C bus...")
#     i2c_bus_reset()

#     i2c = make_i2c()
#     addr, devs = find_addr(i2c)
#     print("Scan:", [hex(d) for d in devs])
#     if addr is None:
#         print("IS31 not found. Check power/ground/address.")
#         return
#     print("Using addr", hex(addr))

#     try:
#         init_is31(i2c, addr)
#         clear_all(i2c, addr)
#     except OSError as e:
#         print("Init failed:", e)
#         return

#     print("Walking LEDs (0..143). Stop with Ctrl+C after a cycle.")
#     prev = None
#     try:
#         for idx in range(144):
#             if prev is not None:
#                 set_idx(i2c, addr, prev, 0)
#             set_idx(i2c, addr, idx, 255)
#             prev = idx
#             sleep_ms(120)
#         clear_all(i2c, addr)
#         print("Done one full pass.")
#     except OSError as e:
#         print("I2C error during walk:", e)
#         print("Tip: rerun; bus reset happens at start.")
#         try:
#             clear_all(i2c, addr)
#         except:
#             pass

# main()

from machine import Pin, I2C
from time import sleep_ms

# -----------------------------
# CONFIG
# -----------------------------
SDA_PIN = 4
SCL_PIN = 5
I2C_ID = 0
I2C_FREQ = 100000  # safer than 400k while debugging
ADDRS = (0x74, 0x77)

WIDTH  = 16
HEIGHT = 9

# Exclude pixels here (x, y). Example excludes a few:
# EXCLUDED = {(6,0), (7,0), (8,0), (7,1)} - column,row
EXCLUDED = set({(7,3), (8,3), (7,4), (8,4), (7,5), (8,5), (0,6), (6,6), (7,6), (8,6), (9,6), (15,6), (0,7), (1,7), (5,7), (6,7), (7,7), (8,7), (9,7), (10,7), (14, 7), (15, 7), (0,8), (1,8), (2,8), (4,8), (5,8), (6,8), (7,8), (8,8), (9,8), (10,8), (11,8), (13,8), (14,8), (15,8)})

# Set True to ALSO disable excluded LEDs in the IS31 LED-control bitmask.
# If you enable this and you notice the "wrong" LEDs get disabled, see note below.
HARD_DISABLE_EXCLUDED = True

BRIGHTNESS = 255
STEP_MS = 120

# -----------------------------
# I2C BUS RESET (helps "works once then EIO")
# -----------------------------
def i2c_bus_reset():
    sda = Pin(SDA_PIN, Pin.IN, Pin.PULL_UP)
    scl = Pin(SCL_PIN, Pin.OUT)
    scl.value(1)
    sleep_ms(2)

    for _ in range(18):
        scl.value(0); sleep_ms(1)
        scl.value(1); sleep_ms(1)

    # STOP condition
    sda_out = Pin(SDA_PIN, Pin.OUT)
    sda_out.value(0); sleep_ms(1)
    scl.value(1); sleep_ms(1)
    sda_out.value(1); sleep_ms(1)

    Pin(SDA_PIN, Pin.IN, Pin.PULL_UP)
    Pin(SCL_PIN, Pin.IN, Pin.PULL_UP)

def make_i2c():
    return I2C(I2C_ID, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=I2C_FREQ)

def find_addr(i2c):
    devs = i2c.scan()
    for a in ADDRS:
        if a in devs:
            return a, devs
    return None, devs

# -----------------------------
# IS31FL3731 helpers
# -----------------------------
def w(i2c, addr, reg, val):
    i2c.writeto(addr, bytes([reg & 0xFF, val & 0xFF]))

def bank(i2c, addr, b):
    i2c.writeto(addr, bytes([0xFD, b & 0xFF]))
    sleep_ms(1)

def xy_to_index(x, y):
    """
    Default logical mapping: row-major
    (0,0) -> 0, (15,0)->15, (0,1)->16, ... (15,8)->143
    If your physical layout is scrambled, you can later replace this with a lookup table.
    """
    return y * WIDTH + x

def allowed_xy(x, y):
    return (0 <= x < WIDTH) and (0 <= y < HEIGHT) and ((x, y) not in EXCLUDED)

def build_led_control_bytes():
    """
    Build 18 bytes (144 bits) for LED Control registers 0x00..0x11.
    1 = enabled, 0 = disabled.
    Bit mapping is assumed idx->byte=idx//8, bit=idx%8.
    """
    bits = [0xFF] * 18  # start with all enabled

    for y in range(HEIGHT):
        for x in range(WIDTH):
            if not allowed_xy(x, y):
                idx = xy_to_index(x, y)
                b = idx // 8
                bit = idx % 8
                bits[b] &= ~(1 << bit)

    return bits

def init_is31(i2c, addr):
    # Function bank
    bank(i2c, addr, 0x0B)
    w(i2c, addr, 0x0A, 0x00)  # shutdown
    sleep_ms(10)

    # Frame 0 bank
    bank(i2c, addr, 0x00)

    # LED Control registers (enable bits)
    if HARD_DISABLE_EXCLUDED:
        ctrl = build_led_control_bytes()
        for r, val in enumerate(ctrl):
            w(i2c, addr, 0x00 + r, val)
    else:
        for r in range(0x00, 0x12):
            w(i2c, addr, r, 0xFF)

    # Clear PWM registers
    for r in range(0x24, 0xB4):
        w(i2c, addr, r, 0x00)

    # Wake + picture mode, frame 0
    bank(i2c, addr, 0x0B)
    w(i2c, addr, 0x00, 0x00)  # picture mode
    w(i2c, addr, 0x01, 0x00)  # display frame 0
    w(i2c, addr, 0x0A, 0x01)  # normal operation
    sleep_ms(10)

def clear_all(i2c, addr):
    bank(i2c, addr, 0x00)
    for r in range(0x24, 0xB4):
        w(i2c, addr, r, 0x00)

def set_index(i2c, addr, idx, pwm):
    bank(i2c, addr, 0x00)
    w(i2c, addr, 0x24 + idx, pwm & 0xFF)

def set_pixel(i2c, addr, x, y, pwm):
    """
    Safe pixel set: respects EXCLUDED, so excluded pixels are never written.
    """
    if not allowed_xy(x, y):
        return
    idx = xy_to_index(x, y)
    set_index(i2c, addr, idx, pwm)

# -----------------------------
# Walking test
# -----------------------------
def walk_test(i2c, addr):
    prev = None

    while True:
        for y in range(HEIGHT):
            for x in range(WIDTH):
                if not allowed_xy(x, y):
                    continue

                # Turn off previous pixel
                if prev is not None:
                    px, py = prev
                    # Only turn it off if it wasn't excluded
                    if allowed_xy(px, py):
                        set_pixel(i2c, addr, px, py, 0)

                # Turn on current pixel
                set_pixel(i2c, addr, x, y, BRIGHTNESS)
                prev = (x, y)
                sleep_ms(STEP_MS)

        # Clear at end of pass
        clear_all(i2c, addr)
        prev = None
        sleep_ms(400)

# -----------------------------
# Main
# -----------------------------
def main():
    print("\n--- IS31 16x9 Grid Walk Test ---")
    print("Excluded pixels:", sorted(list(EXCLUDED))[:10], ("..." if len(EXCLUDED) > 10 else ""))

    # Try to recover a stuck bus every run
    i2c_bus_reset()

    i2c = make_i2c()
    addr, devs = find_addr(i2c)
    print("I2C scan:", [hex(d) for d in devs])

    if addr is None:
        print("ERROR: IS31FL3731 not found at 0x74 or 0x77.")
        return

    print("Found IS31 at", hex(addr))

    # Init with one retry if EIO occurs
    for attempt in range(2):
        try:
            init_is31(i2c, addr)
            clear_all(i2c, addr)
            break
        except OSError as e:
            print("Init error:", e, "-> resetting bus and retrying")
            i2c_bus_reset()
            i2c = make_i2c()
            sleep_ms(50)
    else:
        print("ERROR: Could not initialize IS31.")
        return

    # Run test
    try:
        walk_test(i2c, addr)
    except OSError as e:
        print("I2C error during walk:", e)

main()
