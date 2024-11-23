import serial
import time
import struct
from datetime import datetime

SAMPLING_RATE_HZ = 10

port = serial.Serial('COM3', baudrate = 38400, timeout=5)

time.sleep(0.1)
port.write(b'g' + struct.pack('<f', float(-150.0)) + b'\n')
time.sleep(0.1)
port.write(b'c' + struct.pack('<f', float(20.0)) + b'\n')
time.sleep(0.1)
time.sleep(5)
port.write(b'm\x01\x02\n')
time.sleep(0.1)
port.write(b'm\x02\x02\n')
time.sleep(0.1)

now = datetime.now()
try:
    with open(f'output/run_{now.strftime("%y-%m-%d__%H-%M")}.csv', 'w+') as csvfile:
        csvfile.write('ADC Value, ADC Voltage, Calculated temperature\n')
        counter = 0
        while True:
            total_vals = [0, 0, 0]
            for i in range(SAMPLING_RATE_HZ):
                port.write(b'r\n')
                reply = port.read_until(b'\n')
                # print(reply.decode())
                vals = [float(val) for val in reply[:-1].decode().split(',')]
                total_vals = [a + b for a, b in zip(total_vals, vals)]
                time.sleep(1.0 / SAMPLING_RATE_HZ)
            total_vals[2] /= 100.0
            total_vals = [val / SAMPLING_RATE_HZ for val in total_vals]
            csvfile.write(', '.join([str(i) for i in total_vals]))
            csvfile.write('\n')
            counter += 1
            if counter == 10:
                print(f'10 more values logged. Last average temp: {total_vals[2]}')
                counter = 0
except KeyboardInterrupt:
    port.write(b'o\n')
    time.sleep(0.1)
    port.close()
