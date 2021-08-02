import random
import networkx as nx
import matplotlib.pyplot as plt

from networkx.drawing.nx_pydot import read_dot
from networkx.algorithms.shortest_paths.generic import shortest_path

from typing import *

FamilyID = int

class Family():
    FAMILIES: Dict[FamilyID, "Family"] = dict()

    def __init__(self, id: FamilyID, name):
        assert(id not in Family.FAMILIES)
        
        self.name = name
        self.id = id
        
        Family.FAMILIES[self.id] = self

    @staticmethod
    def get(id: FamilyID):
        return Family.FAMILIES[id]

# =========================================================== #

TownID = int

class Town():
    NAMES = open("ndrangheta/calabria.txt", "r").readlines()
    TOWNS = dict()
    
    def __init__(self, town_id: TownID, family_id: FamilyID,
                 name=None):
        
        assert(town_id not in Town.TOWNS)
        
        self.id:     TownId   = town_id
        self.family: FamilyID = family_id

        self.name:   str      = Town.NAMES[self.id]
        self.hold_strength = 0.5 + random.random() / 2
        
        Town.TOWNS[self.id] = self

        
    @staticmethod
    def get(id: TownID):
        return Town.TOWNS[id]

# =========================================================== #
from ndrangheta import utils

class Environment():
    def __init__(self, graph):
        self.graph = graph

    def move_from(self, start: TownID, end: TownID,
                  amount: int, path=None):

        random.seed(0)
        
        my_family = Town.get(start).family
        cumulative_delta = list()
        
        for town_id in path:
            town = Town.get(town_id)
            
            if town.family != my_family:
                hold = town.hold_strength

                # Se hold molto alta, molto probabile
                # perdere il carico
                if utils.montecarlo(hold):
                    cumulative_delta.append(0)
                    break
                else:
                    cumulative_delta.append(1)
                    
            else:
                hold = town.hold_strength

                cumulative_delta.append(
                    random.uniform((1+hold)/2, 1)
                )

        final_amount = amount
        for node, delta in zip(path, cumulative_delta):
            final_amount = final_amount * delta

            is_hostile_terrain = my_family != Town.get(node).family

            print(f"Node {node} lost {100*(1-delta):.2f}%", end=" ")
            print("(was " + ("" if is_hostile_terrain else "not ") + "hostile)", end=" ")
            print(f"(hold is: {Town.get(node).hold_strength:.2f})")

        print(f"Arrived with {final_amount:.2f} (-{amount-final_amount:.2f})")

        return final_amount

# =========================================================== #
        
""" 
Promemoria.

g.nodes() ==> [townId, ...]

g.nodes()[townId] ==>
  { townId : {family: familyId} }
"""

# Leggi grafo da file .dot
g = nx.Graph(read_dot("ndrangheta/example.dot"))
g = nx.convert_node_labels_to_integers(g)

def map_nodes(f, g):
    for name in g.nodes():
        d = f(g.nodes()[name])
        nx.set_node_attributes(g, d)

def sanitize_dot(node: Dict) -> Dict:
    node["family"] = int(node["family"])
    return node

map_nodes(sanitize_dot, g)

# Crea istanze Town() / Family()
for n in g.nodes():
    family = g.nodes()[n]["family"] 
    if family not in Family.FAMILIES:
        Family(family, str(family))

    Town(n, family)
        
# =========================================================== #

env = Environment(g)

def play():
    while True:
        s = input("λ) ").split(" ")

        if s[0] == "show":
            utils.show(env.graph)

        if s[0] == "p": #path
            nodes = [int(n) for n in s[1:]]
            env.move_from(nodes[0], nodes[-1], 100, nodes[1:])
        
        if s[0] == "q":
            break
