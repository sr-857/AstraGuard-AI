
#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import time

def rotation_matrix(ax_deg, ay_deg, az_deg):
    ax, ay, az = np.radians([ax_deg, ay_deg, az_deg])
    Rx = np.array([[1,0,0],[0,np.cos(ax),-np.sin(ax)],[0,np.sin(ax),np.cos(ax)]])
    Ry = np.array([[np.cos(ay),0,np.sin(ay)],[0,1,0],[-np.sin(ay),0,np.cos(ay)]])
    Rz = np.array([[np.cos(az),-np.sin(az),0],[np.sin(az),np.cos(az),0],[0,0,1]])
    return Rz @ Ry @ Rx

def plot_cube(ax, R):
    cube = np.array([
        [-1,-1,-1], [1,-1,-1], [1,1,-1], [-1,1,-1],
        [-1,-1,1],  [1,-1,1],  [1,1,1],  [-1,1,1]
    ])
    cube = cube @ R.T
    edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    for e in edges:
        ax.plot3D(*zip(cube[e[0]], cube[e[1]]), color="cyan")

def animate(duration=20):
    plt.ion()
    fig = plt.figure(figsize=(6,6))
    ax = fig.add_subplot(111, projection="3d")
    start = time.time()
    while time.time() - start < duration:
        ax.clear()
        ax.set_xlim(-2,2)
        ax.set_ylim(-2,2)
        ax.set_zlim(-2,2)
        t = time.time() - start
        # simulate a drift that is corrected
        pitch = (np.sin(t*0.5) * 20) + (t%10 if t%20>10 else 0)
        yaw = (np.cos(t*0.3) * 10)
        roll = (np.sin(t*0.2) * 5)
        R = rotation_matrix(roll, pitch, yaw)
        plot_cube(ax, R)
        plt.draw()
        plt.pause(0.05)
    plt.ioff()
    plt.show()

if __name__ == "__main__":
    animate()
