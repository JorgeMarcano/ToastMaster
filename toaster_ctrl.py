from re import S
import serial
import time
import struct
import threading

serial_mutex = threading.Lock()

class Watchdog:
    def __init__(self, port, period=None):
        self.keep_alive_child = None
        self.is_watchdoging = False
        self.end = False
        self.mutex = serial_mutex
        self.period = 1 if (period == None) else period
        self.port = port

    def wakeup(self):
        while not self.end:
            with self.mutex:
                if self.is_watchdoging:
                    self.port.write(b'k\n')
            time.sleep(self.period)

    def start_watchdog(self):
        if self.port == None:
            return

        self.keep_alive_child = threading.Thread(target=self.wakeup, daemon=True)
        self.keep_alive_child.start()

    def pause_watchdog(self):
        self.is_watchdoging = False

    def resume_watchdog(self):
        self.is_watchdoging = True

    def end_watchdog(self):
        self.end = True

class Toaster:
    def __init__(self, comport='COM3'):
        self.comport = comport
        self.port = None
        self.watchdog = None
        self.has_begun = False

    def __enter__(self):
        self.port = serial.Serial(self.comport, baudrate = 38400, timeout=5)
        self.watchdog = Watchdog(self.port)

    def __exit__(self):
        self.close_serial()

    def in_error(self):
        if self.watchdog != None:
            self.watchdog.pause_watchdog()

    def begin_ctrl(self):
        if (self.port == None) or (self.watchdog == None):
            self.in_error()
            return

        self.has_begun = True
        self.watchdog.start_watchdog()

    def close_serial(self):
        if self.watchdog != None:
            self.watchdog.end_watchdog()

        if self.port != None:
            self.port.close()

    def send_cmd(self, byte_str, expect_reply=False):
        if (self.port == None) or (not self.has_begun):
            self.in_error()
            return

        out_str = byte_str
        if out_str[-1] != b'\n':
            out_str += b'\n'

        with serial_mutex:
            self.port.write(out_string)
            if expect_reply:
                reply = self.port.read_until(b'\n')
                #vals = struct.unpack('<hff', reply[:-1])
                vals = [float(val) for val in reply[:-1].decode().split(',')]
                return vals
            return []

    def stop(self):
        self.send_cmd(b'o')

    def read(self):
        vals = self.send_cmd(b'r', True)
        
        print(f'ADC reading: {vals[0]}')
        print(f'ADC voltage: {vals[1]}')
        print(f'Calculatged temperature: {vals[2]}')

    def on(self, is_slow=False):
        if is_slow:
            self.send_cmd(b'm\x01\x02')
        else:
            self.send_cmd(b'm\x02\x02')

    def off(self, is_slow=False):
        if is_slow:
            self.send_cmd(b'm\x01\x01')
        else:
            self.send_cmd(b'm\x02\x01')

    def set_gain(self, gain):
        cmd = b'g'
        cmd += struct.pack("<f", gain)
        self.send_cmd(cmd)

    def set_temp(self, temp):
        cmd = b't'
        cmd += struct.pack("<f", temp)
        self.send_cmd(cmd)

    def set_calibration(self, curr_temp):
        cmd = b'c'
        cmd += struct.pack("<f", curr_temp)
        self.send_cmd(cmd)
        
if __name__ == "__main__":

    controller = Toaster('COM3')

    while True:
        user_input = input('> ')

        args = user_input.split(' ')

        match user_input[0]:
            case 'o':  # Turn off command, nothing needed except the character itself
                controller.stop()
            case 't' | 'g' | 'c':
                if len(args) < 2:
                    print('Not enough values for command')
                    continue
                floatval = float(args[1])
                float_bytes = struct.pack("<f", floatval)
                out_string += float_bytes
            case 'r':
                controller.read()
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
