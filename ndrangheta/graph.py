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

class Shipment:
    def __init__(self, kgs: float, costed: int, destination: TownID):
        self.kgs = kgs
        self.initial_kgs = kgs
        
        self.costed = costed
        self.dest = destination

        self.loss_history: List[Tuple[TownID, float]] = list()
        
    def loss_absolute(self) -> float:
        return round(self.initial_kgs - self.kgs, 2)

    def loss_percent(self) -> float:
        return round(100 * (1 - self.kgs / self.initial_kgs), 2)

    def displace(self, loss_multiplier: float, town: TownID):
        self.kgs *= loss_multiplier
        self.loss_history.append((town, loss_multiplier))


class Routing:
    def __init__(self, graph):
        self.graph = graph

    def describe_shipment(self, town: Town, loss: float, my_family: FamilyID):
        """
        Just a fancy print function for shipment movements.
        """
        town_name, is_hostile = town.name, town.family != my_family
        
        print(f"In node {town.id} lost {100*(1-loss):.2f}%")
        print("\tWas " + ("" if is_hostile else "not ") + "hostile")
        print(f"\tHold is {town.hold:.2f}")
        print("")


    def is_valid_shipment(self, start: TownID, end: TownID, ship: Shipment=None):
        t1, t2 = Town.get(start), Town.get(end)
        self.check_is_valid_shipment_geographically(t1, t2)
        self.check_is_valid_shipment_drug_wise(t1, t2, ship)

        return True

    def check_is_valid_shipment_geographically(self, t1, t2):
        if t1 == t2:
            raise ShipmentError("Destination is the same as the source!")
        if t1.family != t2.family:
            raise ShipmentError(f"Destination is a place not owned by family {t1.family}")

    def check_is_valid_shipment_drug_wise(self, t1, _, ship):
        if t1.drugs < ship.initial_kgs:
            raise ShipmentError(f"Wanted to send {ship.initial_kgs}kg, "
                                f"but only {t1.drugs} are available in {t1}")
        if ship.initial_kgs <= 0:
            raise ShipmentError(f"Zero or below kgs of drugs scheduled ({ship.initial_kgs})")

    
    def move_single(self, start: TownID, end: TownID, ship: Shipment, my_family: FamilyID) -> float:
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
                ship.displace(0, town)
                return False
            
            self.describe_shipment(town, 1, my_family)
            ship.displace(1, town)
            return True
        
        loss = random.uniform((1 + town.hold) / 2, 1)
        ship.displace(loss, town)
        self.describe_shipment(town, loss, my_family)
        return True
    
        
    def send_shipment_manual(self,
                start: TownID, end: TownID,
                ship: Shipment, path: List[TownID]) -> int:
        """
        Nota: PATH comprende tutti i nodi TRANNE quello iniziale. Quello finale c'è.
        """

        assert(self.is_valid_shipment(start, end, ship))

        town = Town.get(start)
        town.mail_shipment(ship)
        
        my_family = town.family
        from_node = path[0]
        
        for town_id in path[1:]: #NB: la prima iter sarà move(start, start)!
            ok = self.move_single(from_node, town_id, ship, my_family)

            if not ok:
                print(f"Failed to deliver, package captured in {town_id}!")
                return 0
            
            from_node = town_id

        town = Town.get(end)
        old_hold = town.hold
        new_hold = town.change_hold(ship.loss_percent())

        town.receive_shipment(ship, my_family, retail_multiplier=1.1)  
            
        print(
            f"Arrived at destination ({town.id}) "
            f"with {ship.kgs:.2f}kg, "
            f"lost {ship.loss_absolute():.2f}kg on the way.\n"
            f"Hold at {town.id} changed from {old_hold:.2f} to {new_hold:.2f}"
            f"(difference: {new_hold-old_hold:.2f})" 
        )
        print()
        
        return ship.kgs

    
    def safest_path(self, start_id: TownID, end_id: TownID):
        """
        Safest = only friendly nodes, when impossible enemy's lowest holded nodes.
        """
        start, end = Town.get(start_id), Town.get(end_id)
        self.check_is_valid_shipment_geographically(start, end)

        my_family = start.family
        
        def node_heuristic(__, t_id2, _):
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
            start_id, end_id,
            weight=node_heuristic
        )


    def send_shipment_safest(self, 
            start: TownID,
            end: TownID,
            ship: Shipment) -> int:

        return self.send_shipment_manual(
            start, end, ship,
            self.safest_path(start, end)
        )

# =========================================================== #

class DrugError(Exception): pass

class Narcos():
    def get_price(self, kgs=1):
        return 60_000 * kgs # 60_000$ = 1Kg
    
    def sell_drugs(self, kgs: int, family: Family, dest: TownID):
        money_needed = kgs * self.get_price()

        if family.money < money_needed:
            raise DrugError(f"{money_needed:n}$ needed, but you only have {family.money:n}")

        family.money -= money_needed
        family.drugs += kgs

        Town.get(dest).variate_drugs(kgs)


class Ask():
    @staticmethod
    def confirm():
        print("Confirm? (y/N)")
        answer = input("... ")
        return answer == "y"

        
# =========================================================== #
from ndrangheta.read_dot import load_graph
class AI:
    def __init__(self, simulator: "Simulator"):
        self.s = simulator

    def decide_shipments(self, family_id):
        fam = Family.get(family_id)

        if len(fam.drug_requests) == 0:
            return

        # Per ora:
        # 1. Una richiesta per turno esaudita
        # 2. Priorità a quelle con days_withinig minore
        
        sorted_reqs = sorted(fam.drug_requests, key=lambda r: r.needed_before)
        
        # Provo tutte le richieste; la prima che posso esaudire, la esaudisco;
        # do priorità a quelle più urgenti.
        # Per ora, unica opzione è comprare dai narcos        
        for i, r in enumerate(sorted_reqs):
            cost = self.s.ask_drug_price_to_narcos(r.kgs)
            
            if fam.money > cost:
                self.s.buy_from_narcos(family_id, r.kgs, fam.capital)

                self.s.router.send_shipment_safest(
                    fam.capital, r.author,
                    Shipment(r.kgs, cost, r.author)
                )

                fam.drug_requests.remove(r)
                break            

            
        
        
class Simulator:
    def __init__(self, graph, player_id=0):
        # self.g = graph
        self.router = Routing(graph)
        self.narcos = Narcos()
        self.player_id, self.player = 0, Family.FAMILIES[0]

        self.ai = AI(self)
        self.turn = 0

    def advance_time(self):
        for _, town in Town.TOWNS.items():
            town.advance_turn()
        
        for id, family in Family.FAMILIES.items():
            self.ai_turn(family)

        self.turn += 1

    def ai_turn(self, family: Family):
        pass

    def buy_from_narcos(self, family_id, kgs, dest: TownID) -> bool:
        family = Family.get(family_id)
        return self.narcos.sell_drugs(kgs, family, dest)
    
    def ask_drug_price_to_narcos(self, kgs=1):
        return self.narcos.get_price(kgs)

    def send_shipment(self, id1: TownID, id2: TownID, ship: Shipment,
                      mode="safe", **kwargs) -> int:
        if mode == "safe":
            return self.router.send_shipment_safest(id1, id2, ship)
        else:
            return self.router.send_shipment_safest(id1, id2, ship)

# =========================================================== #

def play():
    sim = Simulator(load_graph("tests/dots/inevitable_family.dot"))
    player_id = 0
    player    = Family.get(player_id)
    
    while True:
        try:
            player.stats()

            s = input("λ) ").split(" ")

            if s[0] == "show":
                show(sim.router.graph)

            if s[0] == "drug" and s[1].startswith("p"):
                print(f"Currently sold at {sim.ask_drug_price_to_narcos():n}€ / kg")

            if s[0] == "buy":
                amount = int(s[1])
                price  = sim.ask_drug_price_to_narcos(kgs=amount)

                print(f"{amount} is {price:n}$.")

                Town.print_cities(player_id)
                dest = int(input("Chose a destination city: "))

                if Ask.confirm():
                    sim.buy_from_narcos(player_id, amount, dest)

            if s[0] == "send": #path
                if s[1] == "manual":
                    nodes = [int(n) for n in s[2:]]
                    sim.router.send_shipment_manual(
                        nodes[0], nodes[-2], #start, end
                        Shipment(int(nodes[-1]), None, nodes[-2]), #amount
                        nodes[1:-2])

                else: #safe
                    sim.send_shipment(int(s[1]), int(s[2]), Shipment(int(s[3]), -1, int(s[2])))


            if s[0] == "list":
                Town.print_cities(player_id)

            if s[0] == "q":
                break

            if s[0] == "t":
                sim.advance_time()
                
        except Exception as e:
            import traceback
            
            traceback.print_exc()
            continue
