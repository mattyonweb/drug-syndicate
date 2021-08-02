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
        self.hold = 0.5 + random.random() / 2
        
        Town.TOWNS[self.id] = self

        
    @staticmethod
    def get(id: TownID):
        return Town.TOWNS[id]

# =========================================================== #
from ndrangheta import utils

class Environment():
    def __init__(self, graph):
        self.graph = graph

        
    def describe_shipment(self, town: Town, loss, my_family: FamilyID):
        """
        Just a fancy print function.
        """
        town_name, is_hostile = town.name, town.family != my_family
        
        print(f"In node {town.id} lost {100*(1-loss):.2f}%")
        print("\tWas " + ("" if is_hostile else "not ") + "hostile")
        print(f"\tHold is {town.hold}")

        
    def move_from(self, start: TownID, end: TownID,
                  amount: int, path: List[TownID]):
        """
        Nota: PATH comprende tutti i nodi TRANNE iniziale e finale.
        """        
        my_family = Town.get(start).family
        current_amount = amount
        
        for town_id in path:
            town = Town.get(town_id)
            
            if town.family != my_family:
                if not utils.montecarlo(town.hold):
                    # Se hold avversaria molto alta, molto probabile perdere il carico
                    self.describe_shipment(town, 0, my_family)
                    return 0
                else:
                    self.describe_shipment(town, 1, my_family)
                    
            else:
                hold = town.hold
                loss = random.uniform((1 + town.hold) / 2, 1)
                current_amount *= loss
                self.describe_shipment(town, loss, my_family)

        town = Town.get(end)
        print(
            f"Arrived at destination ({town.id}) "
            f"with {current_amount}, "
            f"lost {(amount-current_amount):.2f}%"
        )
        return current_amount

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
            env.move_from(nodes[0], nodes[-1], 100, nodes[1:-1])
        
        if s[0] == "q":
            break
