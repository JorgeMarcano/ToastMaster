import matplotlib.pyplot as plt
from random import randint
from time import time, sleep

X = []
Y1 = []
Y2 = []

plt.ion()
figure, ax = plt.subplots()
ax.set_autoscale_on(True)
ax.autoscale_view(True,True,True)
line1, = ax.plot(X, Y1, "bo")
line2, = ax.plot(X, Y2, "r+")

start = time()
for i in range(25):
    print(len(X))
    X.append(time() - start)
    Y1.append(randint(0, 10))
    Y2.append(randint(0, 10))
    line1.set_data(X, Y1)
    line2.set_data(X, Y2)
    ax.relim()        # Recalculate limits
    ax.autoscale_view(True,True,True) #Autoscale
    figure.canvas.draw()
    figure.canvas.flush_events()
    sleep(0.5)

plt.ioff()
plt.show()