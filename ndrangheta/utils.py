from typing import *
from random import random
from networkx import draw
from matplotlib.pyplot import show as show_

def montecarlo(threshold: float) -> bool:
    """ 
    Montecarlo random draw.
    """
    return random() > threshold


def cap(value, low, high):
    """
    Cap a value between two extremes.
    """
    if value > high:
        return high
    if value < low:
        return low
    return value


def show(g):
    """
    Shows a graph.
    """
    n_colors = [
        g.nodes()[n]["family"] for n in g.nodes()
    ]
    
    draw(g, with_labels=True, cmap="Pastel1", node_color=n_colors)
    
    show_()

# =========================================================== #

class Schedule:
    def __init__(self, func: Callable, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        return self.func(*self.args, **self.kwargs)
    
    

    

