from typing import *
from random import random
from networkx import draw
from matplotlib.pyplot import show as show_

def montecarlo(threshold: float) -> bool:
    return random() > threshold

def show(g):
    n_colors = [
        g.nodes()[n]["family"] for n in g.nodes()
    ]
    
    draw(g, with_labels=True, cmap="Pastel1", node_color=n_colors)
    
    show_()
    
