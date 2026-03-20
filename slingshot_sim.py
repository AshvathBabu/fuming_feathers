import numpy as np
import matplotlib.pyplot as plt


def simulate_slingshot(
    X, Y, Z,
    k,              # spring constant
    m,              # mass
    start_pos,
    g=9.81,
    num_points=100
):
    # --- Step 1: Stretch length ---
    L = np.sqrt(X**2 + Y**2 + Z**2)

    # --- Step 2: Speed from spring energy ---
    speed = np.sqrt(k / m) * L

    # --- Step 3: Direction ---
    dx, dy, dz = X / L, Y / L, Z / L

    # --- Step 4: Velocity components ---
    vx = speed * dx
    vy = speed * dy
    vz = speed * dz

    x0, y0, z0 = start_pos

    # --- Step 5: Time of flight ---
    a = -0.5 * g
    b = vz
    c = z0

    discriminant = b**2 - 4*a*c
    if discriminant < 0:
        raise ValueError("Projectile never hits ground")

    T1 = (-b + np.sqrt(discriminant)) / (2*a)
    T2 = (-b - np.sqrt(discriminant)) / (2*a)
    T = max(T1, T2)

    # --- Step 6: Trajectory sampling ---
    times = np.linspace(0, T, num_points)
    points = []

    for t in times:
        x = x0 + vx * t
        y = y0 + vy * t
        z = z0 + vz * t - 0.5 * g * t**2

        z = max(z, 0)
        points.append([x, y, z])

    return np.array(points), times, speed


def main():
    # ---- Inputs ----
    X, Y, Z = 1.0, 0.0, 1.0
    k = 5.0
    m = 1.0
    start_pos = (0, 0, 0.5)

    # ---- Run simulation ----
    points, times, speed = simulate_slingshot(
        X, Y, Z,
        k, m,
        start_pos,
        num_points=100
    )

    print(f"Launch speed: {speed:.2f} m/s")
    print("First 5 points:\n", points[:5])

    # ---- Plot ----
    xs, ys, zs = points[:,0], points[:,1], points[:,2]

    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')

    ax.plot(xs, ys, zs)
    ax.scatter(xs[0], ys[0], zs[0], label="Start")
    ax.scatter(xs[-1], ys[-1], zs[-1], label="End")

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")

    ax.legend()
    plt.show(block=True)


if __name__ == "__main__":
    main()
