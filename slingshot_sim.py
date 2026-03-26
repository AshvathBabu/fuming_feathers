# slingshot_sim.py
# ---------------------------------------
# Physics model: converts pull vector into projectile trajectory
# ---------------------------------------

import numpy as np


def simulate_slingshot(
    x, y, z,
    k=5.0,                  # spring constant
    m=1.0,                  # mass of projectile
    start_pos=(0, 0.5, 0),  # starting position
    g=9.81,
    num_points=100
):
    # --- Step 1: Compute pull length ---
    L = np.sqrt(x**2 + y**2 + z**2)

    if L == 0:
        raise ValueError("Zero pull vector")

    # --- Step 2: Convert spring energy → speed ---
    speed = np.sqrt(k / m) * L

    # --- Step 3: Normalize direction ---
    dx, dy, dz = x / L, y / L, z / L

    # --- Step 4: Velocity components ---
    vx = speed * dx
    vy = speed * dy
    vz = speed * dz

    x0, y0, z0 = start_pos

    # --- Step 5: Time of flight (Y is vertical axis) ---
    a = -0.5 * g
    b = vy
    c = y0

    discriminant = b**2 - 4*a*c
    if discriminant < 0:
        raise ValueError("Projectile never hits ground")

    T1 = (-b + np.sqrt(discriminant)) / (2*a)
    T2 = (-b - np.sqrt(discriminant)) / (2*a)
    T = max(T1, T2)

    # --- Step 6: Sample trajectory ---
    times = np.linspace(0, T, num_points)
    points = []

    for t in times:
        X = x0 + vx * t
        Y = y0 + vy * t - 0.5 * g * t**2
        Z = z0 + vz * t

        # Prevent going below ground
        Y = max(Y, 0)

        points.append([X, Y, Z])

    return np.array(points), times, speed
