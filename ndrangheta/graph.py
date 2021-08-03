import random
import networkx as nx
import matplotlib.pyplot as plt

from networkx.drawing.nx_pydot import read_dot
from networkx.algorithms.shortest_paths.generic import shortest_path

from ndrangheta.config import *
from ndrangheta.entities import *
from ndrangheta.utils import montecarlo, show

from typing import *

# =========================================================== #

class ShipmentError(Exception): pass

class Environment():
    def __init__(self, graph):
        self.graph = graph

    def describe_shipment(self, town: Town, loss, my_family: FamilyID):
        """
        Just a fancy print function for shipment movements.
        """
        town_name, is_hostile = town.name, town.family != my_family
        
        print(f"In node {town.id} lost {100*(1-loss):.2f}%")
        print("\tWas " + ("" if is_hostile else "not ") + "hostile")
        print(f"\tHold is {town.hold:.2f}")
        print("")


    def is_valid_shipment(self, start: TownID, end: TownID):
        t1, t2 = Town.get(start), Town.get(end)

        if t1 == t2:
            raise ShipmentError("Destination is the same as the source!")
        if t1.family != t2.family:
            raise ShipmentError(f"Destination is a place not owned by family {start}")
        
        return True

    
    def move_single(self, start: TownID, end: TownID, amount: int, my_family: FamilyID) -> float:
        """
        Move a package from a city to the other.
        """
        if end not in self.graph.adj[start]:
            raise ShipmentError(f"Node {start} not adjacent to node {end}")

        town = Town.get(end)

        if town.family != my_family:
            if not montecarlo(town.hold):
                # Se hold avversaria molto alta, molto probabile perdere il carico
                self.describe_shipment(town, 0, my_family)
                return 0
            
            self.describe_shipment(town, 1, my_family)
            return amount
        
        loss = random.uniform((1 + town.hold) / 2, 1)
        self.describe_shipment(town, loss, my_family)
        
        return amount * loss
    
        
    def send_shipment_manual(self, start: TownID, end: TownID,
                  amount: int, path: List[TownID]) -> int:
        """
        Nota: PATH comprende tutti i nodi TRANNE quello iniziale. Quello finale c'è.
        """        

        assert(self.is_valid_shipment(start, end))
        
        my_family = Town.get(start).family
        
        current_amount = amount

        from_node = path[0]
        for town_id in path[1:]: #NB: la prima iter sarà move(start, start)!
            current_amount = self.move_single(from_node, town_id, current_amount, my_family)

            if current_amount == 0:
                print(f"Failed to deliver, package captured in {town_id}!")
                return 0
            
            from_node = town_id

        town = Town.get(end)
        loss = 100 * (amount - current_amount) / amount

        old_hold = town.hold
        new_hold = town.change_hold(loss)
        
        print(
            f"Arrived at destination ({town.id}) "
            f"with {current_amount:.2f}kg, "
            f"lost {(amount-current_amount):.2f}kg on the way.\n"
            f"Hold at {town.id} changed from {old_hold:.2f} to {new_hold:.2f}"
            f"(difference: {new_hold-old_hold:.2f})" 
        )
        print()
        return current_amount


    def safest_path(self, start: TownID, end: TownID):
        """
        Safest = only friendly nodes, when impossible enemy's lowest holded nodes.
        """
        assert(self.is_valid_shipment(start, end))

        start_town = Town.get(start)
        my_family = start_town.family
        
        def node_heuristic(t_id1, t_id2, _):
            t2 = Town.get(t_id2)

            if t2.family != my_family:
                # Safe = evita a tutti i costi, a meno che non sia
                # inevitabile, un nodo di una famiglia avversaria
                v = len(Town.TOWNS) * t2.hold
            else:
                v = 1 - t2.hold                

            return v
            
        return nx.dijkstra_path(
            self.graph,
            start, end,
            weight=node_heuristic
        )


    def send_shipment_safest(self, 
            start: TownID,
            end: TownID,
            amount: int):

        return self.send_shipment_manual(
            start, end, amount,
            self.safest_path(start, end)
        )

# =========================================================== #
        
""" 
g.nodes() ==> [townId, ...]

g.nodes()[townId] ==>
  { townId : {family: familyId} }
"""

def load_graph(fpath="ndrangheta/example.dot"):    
    # Leggi grafo da file .dot
    g = nx.Graph(read_dot(fpath))

    def convert_labels_to_int(g):
        new_g = nx.Graph()
        for n in g.nodes():
            new_g.add_node(int(n), **g.nodes()[n])
            new_g.add_edge(int(n), int(n))
        for (x,y) in g.edges():
            new_g.add_edge(int(x), int(y))

        return new_g
    
    # g = nx.convert_node_labels_to_integers(g)
    g = convert_labels_to_int(g)

    def map_nodes(f, g):
        for name in g.nodes():
            d = f(g.nodes()[name])
            nx.set_node_attributes(g, d)

    def sanitize_dot(node: Dict) -> Dict:
        node["family"] = int(node["family"])
        if "hold" in node:
            node["hold"] = float(node["hold"])
            
        return node

    map_nodes(sanitize_dot, g)

    # TODO
    if Family.FAMILIES != dict() or Town.TOWNS != dict():
        print("Polluted Family/Towns, resetting")
        Family.FAMILIES = dict()
        Town.TOWNS      = dict()

        
    # Crea istanze Town() / Family()
    for n in g.nodes():
        family = g.nodes()[n]["family"] 
        if family not in Family.FAMILIES:
            Family(family, str(family))

        Town(n, family)

    return g

g = load_graph()

# =========================================================== #

class DrugError(Exception): pass

# class Player():
#     def __init__(self, id):
#         self.id = id
#         self.money = 1_000_000
#         self.drugs = 0

#     def stats(self):
#         print(f"======== Player {self.id} - {self.money:n}€ - {self.drugs}kg ========")
        

class Narcos():
    def get_price(self, kgs=1):
        return 60_000 * kgs # 60_000$ = 1Kg
    
    def sell_drugs(self, kgs: int, family: Family, dest: TownID):
        money_needed = kgs * self.get_price()

        if family.money < money_needed:
            raise DrugError(f"{money_needed:n}$ needed, but you only have {family.money:n}")

        family.money -= money_needed
        family.drugs += kgs

        Town.get(dest).add_drugs(kgs)


class Ask():
    @staticmethod
    def confirm():
        print("Confirm? (y/N)")
        answer = input("... ")
        return answer == "y"

        
# =========================================================== #

g = load_graph("tests/dots/inevitable_family.dot")
env = Environment(g)

def play():
    env = Environment(g)
    narcos = Narcos()
    player_id, player = 0, Family.FAMILIES[0]
    
    while True:
        player.stats()

        s = input("λ) ").split(" ")

        if s[0] == "show":
            show(env.graph)

        if s[0] == "drug" or s[0] == "drugs":
            print(f"Currently sold at {narcos.get_price():n}€ / kg")

            if len(s) == 1:
                continue
            
            if s[1] == "buy":
                amount = int(s[2])
                price  = narcos.get_price(kgs=amount)
                
                print(f"{amount} is {price}$.")

                Town.print_cities(player_id)
                dest = int(input("Chose a destination city: "))
                
                if Ask.confirm():
                    narcos.sell_drugs(amount, player, dest)

                    
        if s[0] == "path": #path
            if s[1].isnumeric():
                nodes = [int(n) for n in s[1:]]
                env.send_shipment_manual(nodes[0], nodes[-1], 100, nodes[1:-1])
                
            elif s[1] == "safe":
                env.send_shipment_safest(int(s[2]), int(s[3]), 100)


        if s[0] == "list":
            Town.print_cities(player_id)
            
        if s[0] == "q":
            break
