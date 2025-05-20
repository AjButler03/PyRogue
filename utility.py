import random
import math

def exp_chancetime(n, decay_rate=0.01):
    """
    Returns True with a probability that decays exponentially with n.
    decay_rate: controls how fast the probability drops. Default gives ~93% at n=7.
    """
    if n <= 0:
        raise ValueError("Input must be a positive integer.")

    probability = math.exp(-decay_rate * n)
    return random.random() < probability