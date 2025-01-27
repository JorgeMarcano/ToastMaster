import time
from datetime import datetime
from toaster_ctrl import Toaster
from tkinter import filedialog
import matplotlib.pyplot as plt

from threading import Thread

HYSTERESIS = 3

fig = plt.figure()
temp_ax = fig.add_subplot(1, 2, 1)
step_ax = fig.add_subplot(1, 2, 2)

def sound_alarm():
    while True:
        print('OPEN OVEN DOOR!\a')
        time.sleep(1)

def controller_init(controller):
    controller.begin_ctrl()
    time.sleep(0.1)
    controller.set_gain(-150.0)
    time.sleep(0.1)
    controller.set_calibration(20.0)
    time.sleep(0.1)
    controller.profile_clear()
    time.sleep(0.1)
    controller.set_hysteresis(HYSTERESIS)
    time.sleep(0.1)

def do_1_iteration(controller, data):
    vals = controller.read()#do_print=False)
    time_ms = time.time() - start_time
    temperature_degc = vals[2] / 1000.0
    profile_step = vals[3]
    desired_temperature_degc = vals[4] / 1000.0

    # if abs(temperature_degc - desired_temperature_degc) > HYSTERESIS:
    #     print('WARNING! TEMPERATURE OUTSIDE DESIRED RANGE\a')
    
    data[0].append(time_ms)
    data[1].append(temperature_degc)
    data[2].append(desired_temperature_degc)
    data[3].append(profile_step)

    temp_ax.clear()
    temp_ax.plot(data[0], data[1], color='r')
    temp_ax.plot(data[0], data[2], color='b')
    temp_ax.plot(data[0], [item + HYSTERESIS for item in data[2]], color='0.8', linestyle='dashed', linewidth=1)
    temp_ax.plot(data[0], [item - HYSTERESIS for item in data[2]], color='0.8', linestyle='dashed', linewidth=1)

    step_ax.clear()
    step_ax.plot(data[0], data[3], color='tab:orange')

    fig.canvas.draw()
    fig.canvas.flush_events()

    return profile_step

if __name__ == "__main__":
    # Get the csv file
    filename = filedialog.askopenfilename(initialdir = ".",
                                          title = "Select a File",
                                          filetypes = (("CSV files", "*.csv*"),
                                                       ("Text files", "*.txt*"),
                                                       ("all files", "*.*")))
    stripped_name = filename.split("/")[-1].split("\\")[-1].split(".")[0]

    steps = []
    try:
        with open(filename, 'r') as file:
            lines = file.readlines()
            steps = [[int(i) for i in line.strip().split(',')] for line in lines]
    except:
        print("Error reading file")
        steps = []

    if len(steps) < 1:
        print("Empty file or failed to read")
        exit()

    for step in steps:
        if len(step) != 2:
            print("Error in parsing file")
            exit()

    output_csv_filename = f'runs/run_{stripped_name}_{datetime.now().strftime("%y-%m-%d__%H-%M")}.csv'

    data = [[] for _ in range(4)]

    plt.ion()
    plt.show()

    alarm_thread = Thread(target=sound_alarm, daemon=True)

    # Setup the Toaster
    controller = Toaster('COM6')
    with controller:
        controller_init(controller)

        print("initialized")

        for step in steps:
            controller.profile_add_point(step[0] * 1000, step[1])

        print("profile set")

        start_time = time.time()
        controller.profile_run()
        time.sleep(0.1)

        while True:
            profile_step = do_1_iteration(controller, data)
            time.sleep(1)

            if profile_step == len(steps) - 1:
                print('WARNING: OPEN THE DOOR!!\a')

            if profile_step < 0:
                break

        alarm_thread.start()
        
        # Take some readings after profile officially finishes
        for i in range(30):
            do_1_iteration(controller, data)

            time.sleep(1)


    with open(output_csv_filename, 'w+') as csvfile:
        csvfile.write('Time (s), Temperature (C), Desired (C), Profile step,\n')
        for index, time_ms in enumerate(data[0]):
            line = f'{time_ms}, {data[1][index]}, {data[2][index]}, {data[3][index]}\n'
            csvfile.write(line)

    plt.ioff()
    plt.show()
