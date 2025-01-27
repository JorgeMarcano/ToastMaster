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
        self.period = 0.8 if (period == None) else period
        self.port = port

    def wakeup(self):
        while not self.end:
            if self.is_watchdoging:
                with self.mutex:
                    self.port.write(b'k\n')
            time.sleep(self.period)

    def start_watchdog(self):
        if self.port == None:
            return

        self.keep_alive_child = threading.Thread(target=self.wakeup, daemon=True)
        self.keep_alive_child.start()
        self.is_watchdoging = True

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

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_serial()

    def in_error(self, msg=None):
        if msg != None:
            print("ERROR: " + msg)

        if self.watchdog != None:
            self.watchdog.pause_watchdog()

    def begin_ctrl(self):
        if (self.port == None) or (self.watchdog == None):
            self.in_error("Port or watchdog not initialized, cannot begin")
            return

        if self.has_begun:
            self.in_error("Toaster was attempted to begin twice")
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
            self.in_error("Port or watchdog not initialized, cannot send cmd")
            return

        out_str = byte_str
        if out_str[-1] != b'\n':
            out_str += b'\n'

        with serial_mutex:
            self.port.write(out_str)
            if expect_reply:
                reply = self.port.read_until(b'\n')
                #vals = struct.unpack('<hff', reply[:-1])
                vals = [int(val) for val in reply.decode().strip().split(',')]
                return vals

    def stop(self):
        self.send_cmd(b'o')

    def read(self, do_print=True):
        vals = self.send_cmd(b'r', expect_reply=True)
        
        if do_print:
            print(f'ADC reading: {vals[0]}')
            print(f'ADC voltage: {vals[1]}')
            print(f'Calculated temperature: {vals[2] / 1000.0}')
            print(f'Current profile step: {vals[3]}')
            print(f'Desired temperature: {vals[4] / 1000.0}')

        return vals

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

    def set_hysteresis(self, hysteresis):
        cmd = b'h'
        cmd += struct.pack('<f', hysteresis)
        self.send_cmd(cmd)

    def profile_add_point(self, time_ms, temp_degc):
        cmd = b'pa'
        cmd += struct.pack('<if', time_ms, temp_degc)
        self.send_cmd(cmd)
        print(self.port.read_until(b'\n'))

    def profile_clear(self):
        cmd = b'pc'
        self.send_cmd(cmd)

    def profile_run(self):
        cmd = b'pr'
        self.send_cmd(cmd)
        print(self.port.read_until(b'\n'))

        
if __name__ == "__main__":

    with Toaster('COM3') as controller:
        controller.begin_ctrl()
        while True:
            user_input = input('> ')

            args = user_input.split(' ')

            match user_input[0]:
                case 'o':  # Turn off command, nothing needed except the character itself
                    controller.stop()
                case 't':
                    if len(args) < 2:
                        print('Not enough values for command')
                        continue
                    controller.set_temp(float(args[1]))
                case 'c':
                    if len(args) < 2:
                        print('Not enough values for command')
                        continue
                    controller.set_calibration(float(args[1]))
                case 'g':
                    if len(args) < 2:
                        print('Not enough values for command')
                        continue
                    controller.set_gain(float(args[1]))
                case 'r':
                    controller.read()
                case 'x':
                    controller.stop()
                    with serial_mutex:
                        exit()
                case 'm':
                    if len(args) < 3:
                        print('Not enough values for command')
                        continue
                    is_slow = False
                    if args[1] == 'slow':
                        is_slow = True
                    elif args[1] == 'fast':
                        is_slow = False
                    else:
                        print('Input not recognized')
                        continue

                    if args[2] == '0':
                        controller.off(is_slow)
                    elif args[2] == '1':
                        controller.on(is_slow)
                    else:
                        print('Input not recognized')
                        continue
                case _:
                    print('Input not recognized')
                    continue
