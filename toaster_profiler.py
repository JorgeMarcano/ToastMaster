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
    controller.on(True)
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

    with open(f'runs/run_{stripped_name}_{datetime.now().strftime("%y-%m-%d__%H-%M")}.csv', 'w+') as csvfile:
        csvfile.write('Time (s), Temperature (C), Status, Goal (C)\n')

        # Setup the Toaster
        with Toaster('COM3') as controller:
            controller_init(controller)

            last_temp = 20
            last_timestep = 0
            start_time = time.time()
            is_on = False
            curr_step = 0
            
            for step in steps:
                next_temp = step[1]
                next_timestep = step[0]

                equation = float(next_temp - last_temp) / float(next_timestep - last_timestep)

                delta = time.time() - start_time
                while (delta < next_timestep):
                    curr_temp = controller.read()[2]
                    goal_temp = equation * (delta-last_timestep) + last_temp

                    if (curr_temp > goal_temp + WINDOW):
                        # too high
                        controller.off()
                        is_on = False

                    if (curr_temp < goal_temp - WINDOW):
                        # too low
                        controller.on()
                        is_on = True

                    csvfile.write(f"{delta}, {curr_temp}, {is_on}, {goal_temp}\n")
                    time.sleep(0.25)
                    delta = time.time() - start_time

                print(f"Done with step {curr_step}")
                curr_step += 1

