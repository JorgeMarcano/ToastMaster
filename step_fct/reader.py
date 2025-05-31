import serial

ser = serial.Serial(port="COM3", baudrate=115200)

while("Waiting..." not in ser.readline().decode()):
    continue

input("Waiting for you")

with open("output.txt", "w") as file:
    ser.write(b'\n')

    try:
        while (True):
            file.write(ser.readline().decode("utf-8"))
    except:
        print("Finished")
