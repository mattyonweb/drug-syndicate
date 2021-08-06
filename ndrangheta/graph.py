import random
import logging
import networkx as nx
import matplotlib.pyplot as plt

from networkx.drawing.nx_pydot import read_dot
from networkx.algorithms.shortest_paths.generic import shortest_path

from ndrangheta.config import *
from ndrangheta.entities import *
from ndrangheta.utils import montecarlo, show, Schedule

from typing import *

# =========================================================== #

class ShipmentError(Exception): pass

class Shipment:
    def __init__(self, kgs: float, retail_price_kg: float, author: FamilyID):
        self.kgs = kgs
        self.initial_kgs = kgs

        # TODO: semanticamente è scorretto chiamarlo price_per_kg; di fatto
        # questo valore, quando il pacco raggiunge il destinatario, viene
        # imposto come prezzo di vendita per TUTTE le compravendite di droga
        # di quella famiglia
        self.price_per_kg = retail_price_kg
        self.from_family = author

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

        print(f"shipment_family={my_family}, this family={town.family}")
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
        if t1.family != t2.family:
            raise ShipmentError(f"Destination is a place not owned by family {t1.family}")

        
    def check_is_valid_shipment_drug_wise(self, t1, _, ship):
        if t1.drugs < ship.initial_kgs:
            raise ShipmentError(f"Wanted to send {ship.initial_kgs}kg, "
                                f"but only {t1.drugs} are available in {t1}")
        if ship.initial_kgs <= 0:
            raise ShipmentError(f"Zero or below kgs of drugs scheduled ({ship.initial_kgs})")

    
    def move_single(self, start_id: TownID, end_id: TownID, ship: Shipment) -> float:
        """
        Move a package from a city to the other.
        """
        
        if end_id not in self.graph.adj[start_id]:
            raise ShipmentError(f"Node {start_id} not adjacent to node {end_id}")

        start, end = Town.get(start_id), Town.get(end_id)

        remaining_percent = start.transit_shipment(ship)
        
        self.describe_shipment(end, remaining_percent, ship.from_family)
        if remaining_percent == 0:
            return False
        else:
            ship.displace(remaining_percent, end)
            return True
    
        
    def send_shipment_manual(self,
                start: TownID, end: TownID,
                ship: Shipment, path: List[TownID]) -> int:
        """
        Nota: PATH comprende tutti i nodi TRANNE quello iniziale. Quello finale c'è.
        """

        assert(self.is_valid_shipment(start, end, ship))

        print("*"*12)
        print(f"SHIPMENT: {start} to {end}, {ship.kgs}kg\n")
        
        town = Town.get(start)
        town.mail_shipment(ship)
        
        from_node = path[0]
        
        for town_id in path[1:]: #NB: la prima iter sarà move(start, start)!
            ok = self.move_single(from_node, town_id, ship)

            if not ok:
                print(f"Failed to deliver, package captured in {town_id}! Lost {ship.kgs}kg!")
                print("*"*12)
                Town.get(town_id).capture_shipment(ship)
                return 0
            
            from_node = town_id

        town = Town.get(end)
        old_hold = town.hold
        new_hold = town.change_hold(ship.loss_percent())

        town.receive_shipment(ship)  
            
        print(
            f"Arrived at destination ({town.id}) "
            f"with {ship.kgs:.2f}kg, "
            f"lost {ship.loss_absolute():.2f}kg on the way.\n"
            f"Hold at {town.id} changed from {old_hold:.2f} to {new_hold:.2f}"
            f"(difference: {new_hold-old_hold:.2f})" 
        )
        print("*"*12)
        
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
    
    def sell_drugs(self, kgs: int, family: Family, dest: TownID) -> Tuple[Callable, Any]:
        """
        Buying drugs from narcos is a 2-step operation.
        
        Firstly, narcos gets all the money (sell_drugs()); then, at the next turn,
        the family will be delivered the drugs (deliver_drugs()).
        """
        if Town.get(dest).family != family.id:
            raise ShipmentError("Destination is of a different family!")
        
        money_needed = kgs * self.get_price()

        if family.money < money_needed:
            raise DrugError(f"{money_needed:n}$ needed, but you only have {family.money:n}")

        family.money -= money_needed

        # return (self.deliver_drugs, kgs, family, dest)
        return Schedule(self.deliver_drugs, In(turn=1), kgs, family, dest)

    def deliver_drugs(self, kgs, family, dest):
        Town.get(dest).receive_shipment(Shipment(kgs, 80_000, family))
        
    def sell_drugs_immediately(self, kgs: int, family: Family, dest: TownID):
        return self.sell_drugs(kgs, family, dest)()
        # return op[0](*op[1:])

    
class Ask():
    @staticmethod
    def confirm():
        print("Confirm? (y/N)", end=" ")
        answer = input("... ")
        return answer == "y"

        
# =========================================================== #
from ndrangheta.read_dot import load_graph

class AI:
    def __init__(self, simulator: "Simulator"):
        self.s = simulator

    def decide_shipments(self, family_id):
        fam = Family.get(family_id)

        if family_id == -1 or len(fam.drug_requests) == 0:
            return

        # Per ora:
        # 1. Una richiesta per turno esaudita
        # 2. Priorità a quelle con days_withinig minore
        
        sorted_reqs = sorted(fam.drug_requests, key=lambda r: r.needed_before)
        
        # Provo tutte le richieste; la prima che posso esaudire, la esaudisco;
        # do priorità a quelle più urgenti.
        # Per ora, unica opzione è comprare dai narcos        
        for r in sorted_reqs:
            cost = self.s.ask_drug_price_to_narcos(r.kgs)
            
            if fam.money > cost:
                self.s.buy_from_narcos(family_id, r.kgs, fam.capital, immediate=True)

                self.s.router.send_shipment_safest(
                    fam.capital, r.author,
                    # Shipment(r.kgs, 80_000, r.author)
                    Shipment(r.kgs, 80_000, fam.id)
                )

                # fam.drug_requests.remove(r)
                break            

            
        
        
class Simulator:
    def __init__(self, graph):
        self.router = Routing(graph)
        self.narcos = Narcos()
        self.player_id, self.player = 0, Family.FAMILIES[0]

        self.ai = AI(self)
        self.turn = 0


    def advance_time(self, turns=1):
        for _ in range(turns):
            for _, town in Town.TOWNS.items():
                town.advance_turn()

            for family_id in Family.FAMILIES:
                self.ai_family_turn(family_id)

            # Human player
            for op in self.player.scheduled_operations:
                op() #op[0](*op[1:])
            self.player.scheduled_operations = list()

            self.turn += 1

        
    def ai_family_turn(self, family_id: FamilyID):
        # In this turn, every AI chooses what to route in next turn
        if family_id != self.player_id:
            self.ai.decide_shipments(family_id)
            return


    def buy_from_narcos(self, family_id, kgs,
                        dest: TownID, immediate=False) -> Union[Tuple[Callable, KG], None]:
    
        family = Family.get(family_id)

        if immediate:
            return self.narcos.sell_drugs_immediately(kgs, family, dest)
        else:
            return self.narcos.sell_drugs(kgs, family, dest)

        
    def ask_drug_price_to_narcos(self, kgs=1):
        return self.narcos.get_price(kgs)

    
    def send_shipment(self, id1: TownID, id2: TownID, ship: Shipment,
                      mode="safe") -> int:
        if mode == "safe":
            return self.router.send_shipment_safest(id1, id2, ship)
        else:
            return self.router.send_shipment_safest(id1, id2, ship)

        
    def change_tax(self, player_id: FamilyID, city: TownID, amount: float):
        Family.get(player_id).change_tax_in(city, amount)
        
# =========================================================== #

def play():
    import readline

    # sim = Simulator(load_graph("tests/dots/fun.dot"))
    sim = Simulator(load_graph("ndrangheta/example.dot"))
    player_id = 0
    player    = Family.get(player_id)
    
    while True:
        try:
            player.stats(turn=sim.turn)

            s = input("λ) ").split(" ")

            if s[0] == "show":
                show(sim.router.graph)

            if s[0] == "drug" and s[1].startswith("p"):
                print(f"Currently sold at {sim.ask_drug_price_to_narcos():n}€ / kg")

            if s[0] == "tax":
                city, rate = int(s[1]), int(s[2] if s[2][-1] != "%" else s[2][:-1]) / 100
                sim.change_tax(player_id, city, rate)
                
            if s[0] == "buy":
                amount = int(s[1])
                price  = sim.ask_drug_price_to_narcos(kgs=amount)
                dest   = player.capital
                
                print(f"{amount}kg is {price:n}$ - delivered tomorrow in {dest}")

                # Scala i soldi, delivera la droga solo il giorno dopo
                if Ask.confirm():
                    operation = sim.buy_from_narcos(player_id, amount, dest)
                    player.scheduled_operations.append(operation)
                    
                    
            if s[0] == "send": #path
                from_, to, amount = int(s[1]), int(s[2]), int(s[3])
                # ship = Shipment(amount, 80_000, to)
                ship = Shipment(amount, 80_000, Town.get(from_).family)
                    
                if sim.router.is_valid_shipment(from_, to, ship):
                    player.scheduled_operations.append(
                        Schedule(sim.send_shipment, In(turn=1), from_, to, ship)
                    )


            if s[0] == "list":
                Town.print_cities(player_id)

            if s[0].startswith("req"):
                if len(s) == 2:
                    f_id = int(s[1])
                else:
                    f_id = player.id
                
                for r in Family.get(f_id).drug_requests:
                    print(r)
                        
            if s[0] == "q":
                break

            if s[0] == "t":
                t = int(s[1]) if len(s) == 2 else 1
                sim.advance_time(turns=t)
                
        except Exception as e:
            import traceback
            
            traceback.print_exc()
            continue
