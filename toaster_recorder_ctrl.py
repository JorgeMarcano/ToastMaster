import time
from datetime import datetime
from toaster_ctrl import Toaster

SAMPLING_RATE_HZ = 10

with Toaster('COM3') as controller:
    controller.begin_ctrl()
    time.sleep(0.1)
    controller.set_gain(-150.0)
    time.sleep(0.1)
    controller.set_calibration(20.0)
    time.sleep(0.1)
    controller.on(True)
    time.sleep(0.1)
    controller.on()
    time.sleep(0.1)

    now = datetime.now()
    try:
        with open(f'output/run_{now.strftime("%y-%m-%d__%H-%M")}.csv', 'w+') as csvfile:
            csvfile.write('ADC Value, ADC Voltage, Calculated temperature\n')
            counter = 0
            while True:
                total_vals = [0, 0, 0]

                for i in range(SAMPLING_RATE_HZ):
                    vals = controller.read(do_print=False)
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
        controller.stop()
