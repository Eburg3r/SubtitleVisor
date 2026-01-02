from machine import Pin, I2C
from time import sleep_ms

# -----------------------------
# CONFIG
# -----------------------------
SDA_PIN = 4
SCL_PIN = 5
I2C_ID = 0
I2C_FREQ = 100000  # start conservative
ADDRS = (0x74, 0x77)

WIDTH  = 16
HEIGHT = 9

BRIGHTNESS = 255
FRAME_MS = 45       # smaller = faster scroll
LETTER_SPACING = 1  # columns between letters
Y_OFFSET = 1        # vertical placement of 5x7 font in 9-high display

MIRROR_X = True   # back-view left-right mirror
MIRROR_Y = False  # set True if also upside down, this breaks the exclusion list :( so the characters are just flipped vertically

# Exclude pixels so they're NEVER lit (x=0..15, y=0..8)
# Example: EXCLUDED = {(6,0), (7,0), (8,0)}
EXCLUDED = set({(7,3), (8,3), (7,4), (8,4), (7,5), (8,5), (0,6), (6,6), (7,6), (8,6), (9,6), (15,6), (0,7), (1,7), (5,7), (6,7), (7,7), (8,7), (9,7), (10,7), (14, 7), (15, 7), (0,8), (1,8), (2,8), (4,8), (5,8), (6,8), (7,8), (8,8), (9,8), (10,8), (11,8), (13,8), (14,8), (15,8)})

MESSAGE = "Like and subscribe"
# -----------------------------
# I2C BUS RESET (helps with "EIO after first run")
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
# IS31FL3731 low-level
# -----------------------------
def w(i2c, addr, reg, val):
    i2c.writeto(addr, bytes([reg & 0xFF, val & 0xFF]))

def bank(i2c, addr, b):
    i2c.writeto(addr, bytes([0xFD, b & 0xFF]))
    sleep_ms(1)

def xy_to_index(x, y):
    """
    Logical mapping assumed: row-major.
    If your physical order is different, replace this with your mapping table.
    """
    # Apply view transforms
    if MIRROR_X:
        x = (WIDTH - 1) - x
    if MIRROR_Y:
        y = (HEIGHT - 1) - y

    # Row-major mapping (adjust later if you have a custom mapping table)
    return y * WIDTH + x

def allowed_xy(x, y):
    return (0 <= x < WIDTH) and (0 <= y < HEIGHT) and ((x, y) not in EXCLUDED)

def build_led_control_bytes():
    """
    18 bytes (144 bits). 1 = enabled, 0 = disabled.
    Assumes bit order idx -> byte=idx//8, bit=idx%8.
    If this disables the wrong LEDs on your board, you can skip hardware-disable
    and rely only on EXCLUDED in software.
    """
    ctrl = [0xFF] * 18
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if not allowed_xy(x, y):
                idx = xy_to_index(x, y)
                b = idx // 8
                bit = idx % 8
                ctrl[b] &= ~(1 << bit)
    return ctrl

def init_is31(i2c, addr, hardware_disable_excluded=True):
    # function bank
    bank(i2c, addr, 0x0B)
    w(i2c, addr, 0x0A, 0x00)  # shutdown
    sleep_ms(10)

    # frame 0
    bank(i2c, addr, 0x00)

    # LED enable bits
    if hardware_disable_excluded:
        ctrl = build_led_control_bytes()
        for r, val in enumerate(ctrl):
            w(i2c, addr, 0x00 + r, val)
    else:
        for r in range(0x00, 0x12):
            w(i2c, addr, r, 0xFF)

    # clear PWM
    # (we'll also push full frames later)
    for r in range(0x24, 0xB4):
        w(i2c, addr, r, 0x00)

    # picture mode, display frame 0, wake
    bank(i2c, addr, 0x0B)
    w(i2c, addr, 0x00, 0x00)  # picture mode
    w(i2c, addr, 0x01, 0x00)  # display frame 0
    w(i2c, addr, 0x0A, 0x01)  # normal operation
    sleep_ms(10)

def write_pwm_frame(i2c, addr, pwm144):
    """
    Write all 144 PWM bytes starting at register 0x24 in ONE transaction.
    Much faster and usually more robust than per-LED writes.
    """
    bank(i2c, addr, 0x00)
    payload = bytearray(1 + 144)
    payload[0] = 0x24
    payload[1:] = pwm144
    i2c.writeto(addr, payload)

# -----------------------------
# 5x7 FONT (columns, LSB=top) flipped across x axis
# Only includes: space, A-Z, 0-9, !, ?, ., -, :
# You can add more chars by extending this dict.
# -----------------------------
FONT = {
    " ": [0x00,0x00,0x00,0x00,0x00],
    "!": [0x00,0x00,0x5F,0x00,0x00],
    ".": [0x00,0x60,0x60,0x00,0x00],
    "-": [0x08,0x08,0x08,0x08,0x08],
    ":": [0x00,0x36,0x36,0x00,0x00],
    "?": [0x02,0x01,0x51,0x09,0x06],

    "0": [0x3E,0x51,0x49,0x45,0x3E],
    "1": [0x00,0x42,0x7F,0x40,0x00],
    "2": [0x42,0x61,0x51,0x49,0x46],
    "3": [0x21,0x41,0x45,0x4B,0x31],
    "4": [0x18,0x14,0x12,0x7F,0x10],
    "5": [0x27,0x45,0x45,0x45,0x39],
    "6": [0x3C,0x4A,0x49,0x49,0x30],
    "7": [0x01,0x71,0x09,0x05,0x03],
    "8": [0x36,0x49,0x49,0x49,0x36],
    "9": [0x06,0x49,0x49,0x29,0x1E],

    "A": [0x7E,0x09,0x09,0x09,0x7E],
    "B": [0x7F,0x49,0x49,0x49,0x36],
    "C": [0x3E, 0x41, 0x41, 0x41, 0x22],
    "D": [0x7F, 0x41, 0x41, 0x22, 0x1C],
    "E": [0x7F,0x49,0x49,0x49,0x49],
    "F": [0x7F,0x09,0x09,0x09,0x01],
    "G": [0x3E, 0x41, 0x41, 0x4B, 0x3A],
    "H": [0x7F,0x08,0x08,0x08,0x7F],
    "I": [0x00,0x41,0x7F,0x41,0x00],
    "J": [0x20, 0x40, 0x40, 0x41, 0x3F],
    "K": [0x7F,0x08,0x14,0x22,0x41],
    "L": [0x7F,0x40,0x40,0x40,0x40],
    "M": [0x7F,0x02,0x04,0x02,0x7F],
    "N": [0x7F,0x04,0x08,0x10,0x7F],
    "O": [0x3E,0x41,0x41,0x41,0x3E],
    "P": [0x7F,0x09,0x09,0x09,0x06],
    "Q": [0x3E,0x41,0x51,0x21,0x5E],
    "R": [0x7F,0x09,0x19,0x29,0x46],
    "S": [0x26,0x49,0x49,0x49,0x32],
    "T": [0x01,0x01,0x7F,0x01,0x01],
    "U": [0x3F,0x40,0x40,0x40,0x3F],
    "V": [0x1F,0x20,0x40,0x20,0x1F],
    "W": [0x3F,0x40,0x38,0x40,0x3F],
    "X": [0x63,0x14,0x08,0x14,0x63],
    "Y": [0x07,0x08,0x78,0x08,0x07],
    "Z": [0x61,0x51,0x49,0x45,0x43],
}

FONT_W = 5
FONT_H = 7

def render_text_to_bitmap(msg):
    """
    Returns a 2D bitmap: list of rows, each row is list of 0/1 pixels.
    Height = FONT_H, Width = len(msg)*(FONT_W+LETTER_SPACING)
    """
    msg = msg.upper()
    cols = []
    for ch in msg:
        glyph = FONT.get(ch, FONT[" "])
        cols.extend(glyph)
        cols.extend([0x00] * LETTER_SPACING)

    width = len(cols)
    bmp = [[0] * width for _ in range(FONT_H)]
    for x, colbits in enumerate(cols):
        for y in range(FONT_H):
            # bit0 = top row
            bmp[y][x] = 1 if (colbits >> y) & 1 else 0
    return bmp

def show_window(i2c, addr, bmp, x0):
    """
    Display a WIDTHxHEIGHT window of the FONT_H-high bitmap starting at x0.
    """
    pwm = bytearray(144)  # all zeros by default

    for y in range(HEIGHT):
        for x in range(WIDTH):
            if not allowed_xy(x, y):
                continue

            src_y = y - Y_OFFSET
            src_x = x + x0

            on = 0
            if 0 <= src_y < FONT_H and 0 <= src_x < len(bmp[0]):
                on = bmp[src_y][src_x]

            idx = xy_to_index(x, y)
            pwm[idx] = BRIGHTNESS if on else 0

    write_pwm_frame(i2c, addr, pwm)

def scroll_text(i2c, addr, msg):
    bmp = render_text_to_bitmap(msg)
    msg_w = len(bmp[0])

    # start offscreen right, scroll to offscreen left
    for x0 in range(-WIDTH, msg_w + WIDTH):
        # window x0 is where the display's left edge maps into bmp
        # We want the text to move left, so we increase x0.
        show_window(i2c, addr, bmp, x0)
        sleep_ms(FRAME_MS)

# -----------------------------
# Main
# -----------------------------
def main():
    print("\n--- IS31 Text Scroll ---")
    i2c_bus_reset()
    i2c = make_i2c()
    addr, devs = find_addr(i2c)
    print("I2C scan:", [hex(d) for d in devs])
    if addr is None:
        print("ERROR: IS31 not found at 0x74 or 0x77")
        return

    print("Found IS31 at", hex(addr))
    # If you suspect the LED enable-bit packing doesn't match, set hardware_disable_excluded=False
    init_is31(i2c, addr, hardware_disable_excluded=True)

    while True:
        try:
            scroll_text(i2c, addr, MESSAGE)
        except OSError as e:
            # If you still get occasional EIO, reset and re-init
            print("I2C error:", e, "-> recovering")
            i2c_bus_reset()
            i2c = make_i2c()
            init_is31(i2c, addr, hardware_disable_excluded=True)

main()
