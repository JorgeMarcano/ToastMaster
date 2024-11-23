import serial
import time
import struct
import threading


port = serial.Serial('COM3', baudrate = 38400, timeout=5)
serial_mutex = threading.Lock()

def wakeup():
    with serial_mutex:
        port.write(b'k\n')
    time.sleep(1)

keep_alive_child = threading.Thread(target=wakeup, daemon=True)
keep_alive_child.start()

while True:
    user_input = input('> ')

    out_string = b''
    expect_reply = False
    args = user_input.split(' ')

    match user_input[0]:
        case 'o':  # Turn off command, nothing needed except the character itself
            pass
        case 't' | 'g' | 'c':
            if len(args) < 2:
                print('Not enough values for command')
                continue
            floatval = float(args[1])
            float_bytes = struct.pack("<f", floatval)
            out_string += float_bytes
        case 'r':
            expect_reply = True
        case 'x':
            with serial_mutex:
                exit()
        case 'm':
            if args[1] == 'slow':
                out_string += b'\1'
            elif args[1] == 'fast':
                out_string += b'\2'
            else:
                print('Input not recognized')
                continue
            out_string += struct.pack('<b', int(args[2]) + 1)
            #expect_reply = True
        case _:
            print('Input not recognized')
            continue
    
    out_string = user_input[0].encode() + out_string + b'\n'
    #out_string += b'\n'
    with serial_mutex:
        port.write(out_string)
        if expect_reply:
            reply = port.read_until(b'\n')
            #vals = struct.unpack('<hff', reply[:-1])
            vals = [float(val) for val in reply[:-1].decode().split(',')]
            print(f'ADC reading: {vals[0]}')
            print(f'ADC voltage: {vals[1]}')
            print(f'Calculatged temperature: {vals[2]}')
