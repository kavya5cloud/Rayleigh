# Intentional dimensional bug: velocity and gravitational acceleration are added.
radius_m = 3_500_000
dt = 10
velocity = radius_m / dt
bad = velocity + 9.81
