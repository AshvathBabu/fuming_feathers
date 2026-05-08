#!/usr/bin/env python3

# slingshot_sim.py
# ---------------------------------------
# Physics model: converts pull vector into projectile trajectory
# ---------------------------------------

import numpy as np


def simulate_slingshot(
    x, y, z,
    k=0.05,                  # spring constant
    m=1.0,                  # mass of projectile
    start_pos=(0.22947800772124752, -0.4589100056285989, 0.1595762961666112),  # starting position
    g=9.81,
    num_points=100
):
    # --- Axis limits (adjust as needed) ---
    X_MIN, X_MAX = 0.0, 0.8
    Y_MIN, Y_MAX = -0.4589100056285989, 0.9
    Z_MIN, Z_MAX = 0.13, 1.5

    # Swap axes
    temp = y
    y = z
    z = temp
    
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

    # --- Step 5: Time of flight (Z is vertical axis) ---
    a = -0.5 * g
    b = vz
    c = z0

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
        Y = y0 + vy * t 
        Z = z0 + vz * t - 0.5 * g * t**2

        # Prevent going below ground
        # Z = max(Z, 0)

        # Stop if outside bounds
        if not (X_MIN <= X <= X_MAX and
                Y_MIN <= Y <= Y_MAX and
                Z_MIN <= Z <= Z_MAX):
            break

        points.append([X, Y, Z])

    return np.array(points), times, speed
