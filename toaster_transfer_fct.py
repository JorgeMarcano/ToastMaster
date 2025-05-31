from toaster_ctrl import Toaster
from tkinter import filedialog
import matplotlib.pyplot as plt
import time
import enum

from threading import Thread


DEFAULT_TEMP_DEGC = 20
DEFAULT_GAIN = -150.0
DEFAULT_HYSTERESIS_DEGC = 3
SAMPLING_INTERVAL = 1


all_data = [[]] * 5
show_plot = False
fig, ax = plt.subplots()

def sample(host: Toaster):
    while True:
        data = host.read(do_print=False)
        for idx, val in enumerate(data):
            all_data[idx].append(val)

        if show_plot:
            ax.clear()
            min_index = max(len(all_data[0]) - 60, 0)
            temps = all_data[2][min_index:-1]
            desired_temps = all_data[4][min_index:-1]
            range = list(range(len(temps)))
            ax.plot(range, temps, color = 'r')
            ax.plot(range, desired_temps, color='b')
            plt.draw()

        time.sleep(SAMPLING_INTERVAL)

def load_profile(args):
    filename = ''
    if len(args) < 2:
        # Get filename from dialog
        filename = filedialog.askopenfilename(initialdir = ".",
                                        title = "Select a File",
                                        filetypes = (("CSV files", "*.csv*"),
                                                    ("Text files", "*.txt*"),
                                                    ("all files", "*.*")))
    else:
        filename = args[1]

    stripped_name = filename.split("/")[-1].split("\\")[-1].split(".")[0]

    steps = []
    try:
        with open(filename, 'r') as file:
            lines = file.readlines()
            steps = [[int(i) for i in line.strip().split(',')] for line in lines]
    except:
        print("Error reading file")
        return [], ''

    if len(steps) < 1:
        print("Empty file or failed to read")
        return [], ''

    for step in steps:
        if len(step) != 2:
            print("Error in parsing file")
            return [], ''
    return steps, stripped_name


with Toaster(comport='COM3') as host:
    host.begin_ctrl()
    host.set_gain(DEFAULT_GAIN)
    host.on(is_slow=True)

    sampling_thread = Thread(target=sample, args=host, daemon=True)
    sampling_thread.start()


    while True:

        user_input = input('> ')

        args = user_input.split(' ')
        command_id = args[0]

        if command_id in Command_ID.OFF:
            host.off()

        elif command_id in Command_ID.HYSTERESIS.union(Command_ID.CALIBRATE, Command_ID.GAIN):
            if len(args) < 2:
                print('Not enough values for command')
                continue
            floatval = float(args[1])

            if command_id in Command_ID.GAIN:
                host.set_gain(floatval)
            elif command_id in Command_ID.HYSTERESIS:
                host.set_hysteresis(floatval)
            elif command_id in Command_ID.CALIBRATE:
                host.set_calibration(floatval)

        elif command_id in Command_ID.REPORT:
            host.read()

        elif command_id in Command_ID.EXIT:
            break

        elif command_id in Command_ID.DEFAULT:
            host.set_gain(DEFAULT_GAIN)
            host.set_hysteresis(DEFAULT_HYSTERESIS_DEGC)
            host.set_calibration(DEFAULT_TEMP_DEGC)

        elif command_id in Command_ID.LOAD_PROFILE:
            loaded_profile, name = load_profile(args)
            if loaded_profile == []:
                continue
            current_profile = loaded_profile
            profile_name = name

            host.profile_clear()
            for step in loaded_profile:
                host.profile_add_point(step[0] * 1000, step[1])

        elif command_id in Command_ID.RUN_PROFILE:
            start_index = len(all_data)
            host.profile_run()
            print('Running profile...')
            while True:
                if all_data[-1][3] == len(current_profile) - 1:
                    break
                time.sleep(SAMPLING_INTERVAL)
            print('Profile done!')

        elif command_id in Command_ID.SHOW_PLOT:
            plt.show()

        elif command_id in Command_ID.HIDE_PLOT:
            plt.close()

        else:
            print('Input not recognized')
            continue

    host.off()
    host.off(is_slow=True)
