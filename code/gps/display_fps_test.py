from machine import Pin, SPI
import gc9a01
import random
import time

spi = SPI(0, baudrate=40000000, sck=Pin(2), mosi=Pin(3))
tft = gc9a01.GC9A01(
    spi,
    240,
    240,
    dc=Pin(6, Pin.OUT),
    cs=Pin(5, Pin.OUT),
    reset=Pin(7, Pin.OUT),
    backlight=Pin(8, Pin.OUT),
    rotation=0
)

tft.init()
tft.fill(gc9a01.BLACK)

t1 = time.ticks_ms()
t2 = 0
count = 0

while True:
    count += 1

    width = random.randint(0, 240 // 2)
    height = random.randint(0, 240 // 2)
    col = random.randint(0, 240 - width)
    row = random.randint(0, 240 - height)

    tft.fill_rect(
        col,
        row,
        width,
        height,
        gc9a01.color565(
            random.getrandbits(8),
            random.getrandbits(8),
            random.getrandbits(8)
        )
    )

    t2 = time.ticks_ms()
    if t1 + 1000 <= t2:
        print(f"{count}fps")
        t1 = t2
        count = 0

    