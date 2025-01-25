import time
from datetime import datetime
from toaster_ctrl import Toaster
from tkinter import filedialog

WINDOW = 3

def controller_init(controller):
    controller.begin_ctrl()
    time.sleep(0.1)
    controller.set_gain(-150.0)
    time.sleep(0.1)
    controller.set_calibration(20.0)
    time.sleep(0.1)
    controller.profile_clear()
    time.sleep(0.1)
    controller.set_hysteresis(3.0)
    time.sleep(0.1)

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
    output_lines = []

    # Setup the Toaster
    with Toaster('COM3') as controller:
        controller_init(controller)

        for step in steps:
            controller.profile_add_point(step[0] * 1000, step[1])

        start_time = time.time()
        controller.profile_run()
        time.sleep(0.1)

        while True:
            vals = controller.read(do_print=False)
            time_ms = time.time() - start_time
            temperature_degc = vals[2] / 1000.0
            profile_step = vals[3]
            desired_temperature_degc = vals[4] / 1000.0

            output_lines.append(f'{time_ms}, {temperature_degc}, {desired_temperature_degc}, {profile_step}')

            time.sleep(1)

            if profile_step < 0:
                break
        
        # Take some readings after profile officially finishes
        for i in range(30):
            vals = controller.read(do_print=False)
            time_ms = time.time() - start_time
            temperature_degc = vals[2] / 1000.0
            profile_step = vals[3]
            desired_temperature_degc = vals[4] / 1000.0

            output_lines.append(f'{time_ms}, {temperature_degc}, {desired_temperature_degc}, {profile_step}\n')

            time.sleep(1)


    with open(output_csv_filename, 'w+') as csvfile:
        csvfile.write('Time (s), Temperature (C), Desired (C), Profile step,\n')
        for line in output_lines:
            csvfile.write(line)
