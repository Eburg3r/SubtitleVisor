from machine import Pin, I2C
from time import sleep_ms
import sys
import uselect

# -----------------------------
# YOUR CONFIG
# -----------------------------
SDA_PIN = 4
SCL_PIN = 5
I2C_ID = 0
I2C_FREQ = 100000
ADDRS = (0x74, 0x77)

WIDTH  = 16
HEIGHT = 9

BRIGHTNESS = 255
FRAME_MS = 5
LETTER_SPACING = 1
Y_OFFSET = 1

MIRROR_X = True
MIRROR_Y = False  # leave False as you said

HARD_DISABLE_EXCLUDED = True

EXCLUDED = set({
    (7,3), (8,3), (7,4), (8,4), (7,5), (8,5),
    (0,6), (6,6), (7,6), (8,6), (9,6), (15,6),
    (0,7), (1,7), (5,7), (6,7), (7,7), (8,7), (9,7), (10,7), (14,7), (15,7),
    (0,8), (1,8), (2,8), (4,8), (5,8), (6,8), (7,8), (8,8), (9,8), (10,8), (11,8), (13,8), (14,8), (15,8)
})

# -----------------------------
# YOUR FONT
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

ALLOWED_CHARS = set(FONT.keys())

# -----------------------------
# I2C bus reset (EIO helper)
# -----------------------------
def i2c_bus_reset():
    sda = Pin(SDA_PIN, Pin.IN, Pin.PULL_UP)
    scl = Pin(SCL_PIN, Pin.OUT)
    scl.value(1)
    sleep_ms(2)
    for _ in range(18):
        scl.value(0); sleep_ms(1)
        scl.value(1); sleep_ms(1)
    # STOP
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
            return a
    return None

def w(i2c, addr, reg, val):
    i2c.writeto(addr, bytes([reg & 0xFF, val & 0xFF]))

def bank(i2c, addr, b):
    i2c.writeto(addr, bytes([0xFD, b & 0xFF]))
    sleep_ms(1)

# -----------------------------
# View -> hardware transform
# (keeps exclusions consistent under MIRROR_X/Y)
# -----------------------------
def view_to_hw(x, y):
    if MIRROR_X:
        x = (WIDTH - 1) - x
    if MIRROR_Y:
        y = (HEIGHT - 1) - y
    return x, y

EXCLUDED_HW = {view_to_hw(x, y) for (x, y) in EXCLUDED}

def allowed_xy_view(x, y):
    if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
        return False
    xh, yh = view_to_hw(x, y)
    return (xh, yh) not in EXCLUDED_HW

def xy_to_index_view(x, y):
    # row-major in HW space after transform
    xh, yh = view_to_hw(x, y)
    return yh * WIDTH + xh

def build_led_control_bytes():
    ctrl = [0xFF] * 18
    for yh in range(HEIGHT):
        for xh in range(WIDTH):
            if (xh, yh) in EXCLUDED_HW:
                idx = yh * WIDTH + xh
                b = idx // 8
                bit = idx % 8
                ctrl[b] &= ~(1 << bit)
    return ctrl

def init_is31(i2c, addr):
    bank(i2c, addr, 0x0B)
    w(i2c, addr, 0x0A, 0x00)  # shutdown
    sleep_ms(10)

    bank(i2c, addr, 0x00)

    # LED enable bits (forced true per your setup)
    ctrl = build_led_control_bytes()
    for r, val in enumerate(ctrl):
        w(i2c, addr, 0x00 + r, val)

    # Clear PWM registers
    for r in range(0x24, 0xB4):
        w(i2c, addr, r, 0x00)

    bank(i2c, addr, 0x0B)
    w(i2c, addr, 0x00, 0x00)  # picture mode
    w(i2c, addr, 0x01, 0x00)  # frame 0
    w(i2c, addr, 0x0A, 0x01)  # normal op
    sleep_ms(10)

def write_pwm_frame(i2c, addr, pwm144):
    bank(i2c, addr, 0x00)
    payload = bytearray(1 + 144)
    payload[0] = 0x24
    payload[1:] = pwm144
    i2c.writeto(addr, payload)

# -----------------------------
# Text rendering / sanitation
# -----------------------------
import re

BRACKET_RE = re.compile(r"\[[^\]]*\]")  # matches [ANYTHING] (no nesting)

def sanitize_text(s):
    s = BRACKET_RE.sub(" ", s)   # remove bracketed tags
    # Never display commas (remove them)
    s = s.replace(",", "")
    # Common transcription punctuation that isn't in your font:
    s = s.replace("'", "").replace("’", "")
    s = s.upper()

    out = []
    last_space = False
    for ch in s:
        if ch in ALLOWED_CHARS:
            out.append(ch)
            last_space = False
        elif ch.isspace():
            if not last_space:
                out.append(" ")
                last_space = True
        else:
            # map unsupported chars to a space
            if not last_space:
                out.append(" ")
                last_space = True
    return "".join(out).strip()

def render_text_bitmap(msg):
    msg = sanitize_text(msg)
    if not msg:
        msg = " "
    cols = []
    for ch in msg:
        cols.extend(FONT.get(ch, FONT[" "]))
        cols.extend([0x00] * LETTER_SPACING)

    wcols = len(cols)
    bmp = [[0] * wcols for _ in range(FONT_H)]
    for x, colbits in enumerate(cols):
        for y in range(FONT_H):
            bmp[y][x] = 1 if ((colbits >> y) & 1) else 0
    return bmp

def show_window(i2c, addr, bmp, x0):
    pwm = bytearray(144)
    bmp_w = len(bmp[0])

    for y in range(HEIGHT):
        for x in range(WIDTH):
            if not allowed_xy_view(x, y):
                continue
            sy = y - Y_OFFSET
            sx = x + x0
            on = 0
            if 0 <= sy < FONT_H and 0 <= sx < bmp_w:
                on = bmp[sy][sx]
            pwm[xy_to_index_view(x, y)] = BRIGHTNESS if on else 0

    write_pwm_frame(i2c, addr, pwm)

# -----------------------------
# Live ticker behavior
# -----------------------------
MAX_CHARS = 180  # prevent huge strings
ticker = "READY"
bmp = render_text_bitmap(ticker)
dirty = False
x0 = -WIDTH
blank_bmp = [[0] * 1 for _ in range(FONT_H)]  # width=1, always draws blank
at_end = False

def replace_message(line):
    global ticker, dirty, x0
    line = sanitize_text(line)
    if not line:
        return
    if line == ticker:      # ignore identical replace
        return
    ticker = line
    dirty = True
    x0 = -WIDTH  # restart scroll on full replace

def append_word(word):
    global ticker, dirty
    word = sanitize_text(word)
    if not word:
        return
    if ticker.strip() == "" or ticker == "READY":
        ticker = word
    else:
        ticker = (ticker + " " + word)

    # trim from left to keep last MAX_CHARS nicely
    if len(ticker) > MAX_CHARS:
        ticker = ticker[-MAX_CHARS:]
        # try to cut to a word boundary
        cut = ticker.find(" ")
        if cut != -1 and cut < 30:
            ticker = ticker[cut+1:]

    dirty = True

def poll_serial(poller):
    while poller.poll(0):
        line = sys.stdin.readline()
        if not line:
            return
        line = line.strip()
        if not line:
            continue

        if line == "CLEAR":
            replace_message(" ")
        elif line.startswith("L:"):
            replace_message(line[2:].strip())
        elif line.startswith("W:"):
            append_word(line[2:].strip())
        # ignore anything else

def main():
    global bmp, dirty, x0, at_end, blank_bmp

    i2c_bus_reset()
    i2c = make_i2c()
    addr = find_addr(i2c)
    if addr is None:
        print("ERROR: IS31 not found")
        return

    init_is31(i2c, addr)
    print("READY")

    poller = uselect.poll()
    poller.register(sys.stdin, uselect.POLLIN)

    while True:
        poll_serial(poller)

        if dirty:
            bmp = render_text_bitmap(ticker)
            dirty = False
            at_end = False
            x0 = -WIDTH     # restart from offscreen right for new content

        if at_end:
            show_window(i2c, addr, blank_bmp, 0)
            sleep_ms(FRAME_MS)
            continue
        
        show_window(i2c, addr, bmp, x0)
        end_off = len(bmp[0]) + WIDTH
        x0 += 1
        if x0 >= end_off:
            at_end = True  # freeze with display blank next loop

        sleep_ms(FRAME_MS)

try:
    main()
except OSError as e:
    print("I2C error:", e)
