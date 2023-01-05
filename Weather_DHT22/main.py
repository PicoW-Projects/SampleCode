from machine import Pin, I2C
from PicoDHT22 import PicoDHT22
from random import randint
import framebuf
import utime
import time
import rp2
import network
import socket
import ubinascii
import urequests as requests
from secrets import secrets

rp2.PIO(0).remove_program()

# Set country to avoid possible errors
rp2.country('US')

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
# If you need to disable powersaving mode
wlan.config(pm = 0xa11140)

# See the MAC address in the wireless chip OTP
mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
print('mac = ' + mac)

# Other things to query
print('Channel: ' + str(wlan.config('channel')))
print('SSID: ' + str(wlan.config('essid')))
print('TX power: ' + str(wlan.config('txpower')))

# Load login data from different file for safety reasons
ssid = secrets['ssid']
pw = secrets['pw']

wlan.connect(ssid, pw)

# Wait for connection with 10 second timeout
timeout = 10
while timeout > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    timeout -= 1
    print('Waiting for connection...')
    time.sleep(1)

# Define blinking function for onboard LED to indicate error codes    
def blink_onboard_led(num_blinks):
    led = machine.Pin('LED', machine.Pin.OUT)
    for i in range(num_blinks):
        led.on()
        time.sleep(.2)
        led.off()
        time.sleep(.2)
    
# Handle connection error
# Error meanings
# 0  Link Down
# 1  Link Join
# 2  Link NoIp
# 3  Link Up
# -1 Link Fail
# -2 Link NoNet
# -3 Link BadAuth

wlan_status = wlan.status()
blink_onboard_led(wlan_status)

if wlan_status != 3:
    raise RuntimeError('Wi-Fi connection failed')
else:
    print('Connected')
    status = wlan.ifconfig()
    print('ip = ' + status[0])

print('SSID: ' + str(wlan.config('essid')))

# Function to load in html page    
def get_html(html_name):
    with open(html_name, 'r') as file:
        html = file.read()
        
    return html

# HTTP server with socket
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

s = socket.socket()
s.bind(addr)
s.listen(1)

print('Listening on', addr)

# Initialize DHT22
dht22 = PicoDHT22(Pin(2,Pin.IN,Pin.PULL_UP))

statusled = Pin(11, Pin.OUT)

def readTH():
    Tsum = 0
    Hsum = 0
    statusled.on()
    for i in range(3):
        T, H = dht22.read()
        time.sleep(.2)
        Tsum = Tsum + int(T)
        Hsum = Hsum + int(H)
    
    avgT = (Tsum / 3)
    avgH = (Hsum / 3)
    statusled.off()
    return round(avgT, 1), round(avgH, 1)

# Listen for connections
while True:
    try:
        T, H = readTH()
        time.sleep(.1)
        cl, addr = s.accept()
        print('Client connected from', addr)
        r = cl.recv(1024)
        # print(r)
            
        response = get_html('index.html')
        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        response = response.replace('id_temp', str(T))
        response = response.replace('id_humi', str(H))
        cl.send(response)
        cl.close()

    except OSError as e:
        cl.close()
        s.close()
        print('Connection closed')
