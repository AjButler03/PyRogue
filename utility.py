import random
import math

# This file contains a few utilitarian methods that the others will use.

def exp_chancetime(n, decay_rate=0.9):
    """
    Returns True with a probability that decays exponentially with n.
    decay_rate: controls how fast the probability drops. Default gives ~93% at n=7.
    """
    if n <= 0:
        raise ValueError("Input must be a positive integer.")

    probability = math.exp(-decay_rate * n)
    return random.random() < probability

# Custom Implementation of a Priority Queue, with decrease-key functionality
# For full transparancy, this was ChatGPT generated while debugging why heapq wasn't really working.
class PriorityQueue:
    def __init__(self):
        self.heap = []  # List of (priority, node)
        self.pos_map = {}  # node -> index in heap

    def push(self, node, priority):
        if node in self.pos_map:
            self.decrease_key(node, priority)
        else:
            self.heap.append((priority, node))
            idx = len(self.heap) - 1
            self.pos_map[node] = idx
            self._heapify_up(idx)

    def pop(self):
        if not self.heap:
            raise IndexError("pop from empty heap")
        self._swap(0, len(self.heap) - 1)
        priority, node = self.heap.pop()
        del self.pos_map[node]
        if self.heap:
            self._heapify_down(0)
        return priority, node

    def decrease_key(self, node, new_priority):
        idx = self.pos_map.get(node)
        if idx is None:
            raise KeyError("Node not found in heap")
        if self.heap[idx][0] <= new_priority:
            return  # No need to update if new priority isn't better
        self.heap[idx] = (new_priority, node)
        self._heapify_up(idx)

    def _heapify_up(self, idx):
        while idx > 0:
            parent = (idx - 1) // 2
            if self.heap[parent][0] > self.heap[idx][0]:
                self._swap(parent, idx)
                idx = parent
            else:
                break

    def _heapify_down(self, idx):
        size = len(self.heap)
        while True:
            smallest = idx
            left = 2 * idx + 1
            right = 2 * idx + 2

            if left < size and self.heap[left][0] < self.heap[smallest][0]:
                smallest = left
            if right < size and self.heap[right][0] < self.heap[smallest][0]:
                smallest = right

            if smallest != idx:
                self._swap(idx, smallest)
                idx = smallest
            else:
                break

    def _swap(self, i, j):
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]
        self.pos_map[self.heap[i][1]] = i
        self.pos_map[self.heap[j][1]] = j

    def __len__(self):
        return len(self.heap)

    def __contains__(self, node):
        return node in self.pos_map
