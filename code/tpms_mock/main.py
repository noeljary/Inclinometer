from machine import Pin, UART
import random
import time

tpms_idx = 0
tpms_const = [
    0xABCDEF1,
    0xBCDEF2A,
    0xCDEF3AB,
    0xDEF4ABC,
    0xEF5ABCD
]

def send(id):
    status = random.randint(0, 0x00FF)
    pressure = random.randint(0, 60)
    temperature = random.randint(-10, 50)
    send_str = f"{id},{status},{pressure},{temperature}"
    
    chksum = 0
    for char in send_str:
        chksum ^= ord(char)
    
    final_send = f"{send_str},{chksum}"
    print(final_send)
    
    led.on()
    uart.write(final_send)
    led.off()


led = Pin(25, Pin.OUT)
led.off()

uart = UART(0, baudrate=4800, tx=Pin(0), rx=Pin(1), timeout=1000)

while True:
    for i in range(0, 90):
        s_time = time.ticks_ms()
        print(i)
        if tpms_idx * 18 == i:
            send(tpms_const[tpms_idx])
            tpms_idx += 1
        elif random.random() > 0.95:
            send(random.randint(0, 0xFFFFFFF))
        
        while s_time + 1000 > time.ticks_ms():
            time.sleep_ms(1)
            
    tpms_idx = 0