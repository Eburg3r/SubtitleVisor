# -----------------------------
# IS31FL3731 + Pico: direct 16x9 grid control
# Edit GRID below (9 lines of 16 chars) with 1=ON, 0=OFF
# -----------------------------
from machine import Pin, I2C
from time import sleep_ms

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

BRIGHTNESS_ON = 255  # 0..255

MIRROR_X = True
MIRROR_Y = False

# Pixels so they're NEVER lit (x=0..15, y=0..8) in VIEW coordinates
EXCLUDED = set({
    (7,3), (8,3), (7,4), (8,4), (7,5), (8,5),
    (0,6), (6,6), (7,6), (8,6), (9,6), (15,6),
    (0,7), (1,7), (5,7), (6,7), (7,7), (8,7), (9,7), (10,7), (14,7), (15,7),
    (0,8), (1,8), (2,8), (4,8), (5,8), (6,8), (7,8), (8,8), (9,8), (10,8), (11,8), (13,8), (14,8), (15,8)
})

# -----------------------------
# EDIT THIS GRID (TOP row first)
# 9 rows, each exactly 16 characters.
# Use '1' for ON, '0' for OFF.
# -----------------------------
GRID = [
    "0000000000000000",  # y=0
    "0000000000000000",  # y=1
    "0000000000000000",  # y=2
    "0000000000000000",  # y=3
    "0000000000000000",  # y=4
    "0000000000000000",  # y=5
    "0000000000000000",  # y=6
    "0000000000000000",  # y=7
    "0000000000000000",  # y=8

]

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
    # Row-major in HW space after mirror transform
    xh, yh = view_to_hw(x, y)
    return yh * WIDTH + xh

def build_led_control_bytes():
    # 144 LEDs -> 18 bytes of enable bits (1=enabled)
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
    # shutdown first
    bank(i2c, addr, 0x0B)
    w(i2c, addr, 0x0A, 0x00)
    sleep_ms(10)

    # enable/disable LEDs (bank 0, 0x00..0x11)
    bank(i2c, addr, 0x00)
    ctrl = build_led_control_bytes()
    for r, val in enumerate(ctrl):
        w(i2c, addr, 0x00 + r, val)

    # clear PWM registers 0x24..0xB3
    for r in range(0x24, 0xB4):
        w(i2c, addr, r, 0x00)

    # picture mode, frame 0, normal operation
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
# Grid display
# -----------------------------
def validate_grid(grid):
    if len(grid) != HEIGHT:
        raise ValueError("GRID must have 9 rows")
    for row in grid:
        if len(row) != WIDTH:
            raise ValueError("Each GRID row must have 16 chars")

def show_grid(i2c, addr, grid, on_val=BRIGHTNESS_ON):
    validate_grid(grid)
    pwm = bytearray(144)  # all zeros
    for y in range(HEIGHT):
        row = grid[y]
        for x in range(WIDTH):
            if not allowed_xy_view(x, y):
                continue
            ch = row[x]
            on = (ch == "1" or ch == "X" or ch == "#")
            pwm[xy_to_index_view(x, y)] = on_val if on else 0
    write_pwm_frame(i2c, addr, pwm)

# Optional helpers (REPL-friendly)
def grid_clear():
    global GRID
    GRID = ["0" * WIDTH for _ in range(HEIGHT)]

def grid_set(x, y, v):
    """Set a single pixel in GRID (view coords). v=True/False or 1/0"""
    global GRID
    if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
        return
    row = list(GRID[y])
    row[x] = "1" if v else "0"
    GRID[y] = "".join(row)

def grid_print():
    """Print the current GRID in a readable way."""
    for y in range(HEIGHT):
        print(GRID[y].replace("0", ".").replace("1", "#"))

def main():
    i2c_bus_reset()
    i2c = make_i2c()
    addr = find_addr(i2c)
    if addr is None:
        print("ERROR: IS31 not found on I2C. scan=", i2c.scan())
        return

    init_is31(i2c, addr)
    print("READY: showing GRID pattern.")
    show_grid(i2c, addr, GRID)

    # Sit here so you can edit GRID and soft-reboot, or use REPL helpers.
    while True:
        sleep_ms(200)

try:
    main()
except OSError as e:
    print("I2C error:", e)
