#!/usr/bin/env python3
"""
AstraGuard AI - 3D Attitude Visualization

Real-time 3D visualization of CubeSat attitude dynamics.
Simulates spacecraft rotation and attitude control maneuvers.

Author: Subhajit Roy
"""

import time
from typing import Tuple, cast

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # type: ignore
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # type: ignore


def rotation_matrix(ax_deg: float, ay_deg: float, az_deg: float) -> np.ndarray:
    """
    Calculate 3D rotation matrix from Euler angles.

    Args:
        ax_deg: Rotation around X-axis in degrees (roll)
        ay_deg: Rotation around Y-axis in degrees (pitch)
        az_deg: Rotation around Z-axis in degrees (yaw)

    Returns:
        3x3 rotation matrix
    """
    ax, ay, az = np.radians([ax_deg, ay_deg, az_deg])

    # Individual rotation matrices
    Rx = np.array(
        [[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]]
    )

    Ry = np.array(
        [[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]]
    )

    Rz = np.array(
        [[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]]
    )

    # Combined rotation (ZYX order)
    return Rz @ Ry @ Rx


def create_cube_vertices() -> np.ndarray:
    """
    Create vertices for a unit cube representing the CubeSat.

    Returns:
        8x3 array of vertex coordinates
    """
    return np.array(
        [
            [-1, -1, -1],
            [1, -1, -1],
            [1, 1, -1],
            [-1, 1, -1],  # Bottom face
            [-1, -1, 1],
            [1, -1, 1],
            [1, 1, 1],
            [-1, 1, 1],  # Top face
        ]
    )


def create_cube_faces() -> list:
    """
    Define faces for the cube for solid rendering.

    Returns:
        List of vertex indices for each face
    """
    return [
        [0, 1, 2, 3],  # Bottom
        [4, 5, 6, 7],  # Top
        [0, 1, 5, 4],  # Front
        [2, 3, 7, 6],  # Back
        [0, 3, 7, 4],  # Left
        [1, 2, 6, 5],  # Right
    ]


def plot_cube_wireframe(ax: Axes3D, R: np.ndarray) -> None:
    """
    Plot cube wireframe with rotation applied.

    Args:
        ax: 3D axes object
        R: Rotation matrix
    """
    cube = create_cube_vertices()
    rotated_cube = cube @ R.T

    # Define edges
    edges = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),  # Bottom face
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),  # Top face
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),  # Vertical edges
    ]

    # Plot edges
    for edge in edges:
        points = rotated_cube[list(edge)]
        ax.plot3D(*points.T, color="cyan", linewidth=2)


def plot_cube_solid(ax: Axes3D, R: np.ndarray, alpha: float = 0.3) -> None:
    """
    Plot solid cube with rotation applied.

    Args:
        ax: 3D axes object
        R: Rotation matrix
        alpha: Transparency level
    """
    cube = create_cube_vertices()
    faces = create_cube_faces()
    rotated_cube = cube @ R.T

    # Create face colors
    face_colors = ["red", "blue", "green", "yellow", "orange", "purple"]

    # Plot faces
    for i, face in enumerate(faces):
        vertices = rotated_cube[face]
        poly = [[vertices[j] for j in range(len(vertices))]]
        ax.add_collection3d(
            Poly3DCollection(
                poly, alpha=alpha, facecolor=face_colors[i], edgecolor="black"
            )
        )


def plot_coordinate_axes(ax: Axes3D, R: np.ndarray) -> None:
    """
    Plot coordinate axes to show orientation.

    Args:
        ax: 3D axes object
        R: Rotation matrix
    """
    # Define axes vectors
    axes_length = 1.5
    axes = np.array(
        [
            [axes_length, 0, 0],  # X-axis (red)
            [0, axes_length, 0],  # Y-axis (green)
            [0, 0, axes_length],  # Z-axis (blue)
        ]
    )

    # Apply rotation
    rotated_axes = axes @ R.T

    # Plot axes
    colors = ["red", "green", "blue"]
    labels = ["X", "Y", "Z"]

    for i, (axis, color, label) in enumerate(zip(rotated_axes, colors, labels)):
        ax.plot3D(
            [0, axis[0]],
            [0, axis[1]],
            [0, axis[2]],
            color=color,
            linewidth=3,
            label=f"{label}-axis",
        )
        ax.text(
            axis[0],
            axis[1],
            axis[2],
            label,
            color=color,
            fontsize=12,
            fontweight="bold",
        )


def simulate_attitude_dynamics(t: float) -> Tuple[float, float, float]:
    """
    Simulate realistic CubeSat attitude dynamics.

    Args:
        t: Current time in seconds

    Returns:
        Tuple of (roll, pitch, yaw) angles in degrees
    """
    # Simulate different motion patterns

    # Normal drift with small oscillations
    roll = np.sin(t * 0.2) * 5 + np.sin(t * 1.5) * 1

    # Pitch with periodic correction maneuvers
    pitch = np.sin(t * 0.3) * 10
    if 10 < t % 20 < 12:  # Correction maneuver
        pitch += (t % 20 - 10) * 2
    elif 12 <= t % 20 < 14:  # Overshoot correction
        pitch += (14 - t % 20) * 1.5

    # Yaw with slow drift
    yaw = np.cos(t * 0.1) * 8 + np.sin(t * 0.7) * 2

    # Add some random jitter
    roll += np.random.normal(0, 0.5)
    pitch += np.random.normal(0, 0.5)
    yaw += np.random.normal(0, 0.5)

    return roll, pitch, yaw


def animate(duration: int = 30, solid: bool = False, show_axes: bool = True) -> None:
    """
    Animate 3D CubeSat attitude visualization.

    Args:
        duration: Animation duration in seconds
        solid: Whether to render solid cube or wireframe
        show_axes: Whether to show coordinate axes
    """
    plt.ion()
    fig = plt.figure(figsize=(10, 8))
    ax = cast(Axes3D, fig.add_subplot(111, projection="3d"))

    start_time = time.time()
    frame_count = 0

    print(f"Starting 3D attitude visualization for {duration} seconds...")
    print("Close window to stop animation early.")

    while time.time() - start_time < duration:
        ax.clear()

        # Set axis properties
        ax.set_xlim(-2, 2)
        ax.set_ylim(-2, 2)
        ax.set_zlim(-2, 2)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")

        # Calculate current time
        elapsed_time = time.time() - start_time

        # Get attitude angles
        roll, pitch, yaw = simulate_attitude_dynamics(elapsed_time)

        # Calculate rotation matrix
        R = rotation_matrix(roll, pitch, yaw)

        # Plot cube
        if solid:
            plot_cube_solid(ax, R)
        plot_cube_wireframe(ax, R)

        # Plot axes if requested
        if show_axes:
            plot_coordinate_axes(ax, R)

        # Add title with current attitude
        ax.set_title(
            "CubeSat Attitude Visualization\n"
            + f"Roll: {roll:.1f}°, Pitch: {pitch:.1f}°, Yaw: {yaw:.1f}°\n"
            + f"Time: {elapsed_time:.1f}s",
            fontsize=12,
        )

        # Set viewing angle
        ax.view_init(elev=20, azim=45 + elapsed_time * 5)

        # Update display
        plt.draw()
        plt.pause(0.05)

        frame_count += 1

        # Check if window was closed
        if not plt.get_fignums():
            break

    plt.ioff()

    if plt.get_fignums():
        plt.show()

    print(f"Animation completed. Rendered {frame_count} frames.")


def main() -> None:
    """
    Main function for 3D attitude visualization.
    Provides interactive options for visualization mode.
    """
    print("=" * 60)
    print("AstraGuard AI - 3D Attitude Visualization")
    print("=" * 60)
    print()
    print("This visualization shows CubeSat attitude dynamics with:")
    print("- Realistic rotation patterns")
    print("- Periodic correction maneuvers")
    print("- Coordinate axes orientation")
    print("- Wireframe and solid rendering options")
    print()

    # Get user preferences
    try:
        duration = int(
            input("Enter animation duration in seconds (default 30): ") or "30"
        )
        solid_mode = input("Use solid rendering? (y/N): ").lower().startswith("y")
        show_axes = not input("Hide coordinate axes? (y/N): ").lower().startswith("y")
    except (ValueError, KeyboardInterrupt):
        print("Using default settings...")
        duration = 30
        solid_mode = False
        show_axes = True

    print("\nStarting visualization with:")
    print(f"- Duration: {duration} seconds")
    print(f"- Rendering: {'Solid' if solid_mode else 'Wireframe'}")
    print(f"- Axes: {'Shown' if show_axes else 'Hidden'}")
    print()

    # Run animation
    animate(duration=duration, solid=solid_mode, show_axes=show_axes)


if __name__ == "__main__":
    main()
