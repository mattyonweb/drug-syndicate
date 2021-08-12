import random
import logging
import networkx as nx
import matplotlib.pyplot as plt

from networkx.drawing.nx_pydot import read_dot
from networkx.algorithms.shortest_paths.generic import shortest_path

from ndrangheta.config import *
from ndrangheta.world import World
from ndrangheta.entities import *
from ndrangheta.utils import montecarlo, show, Schedule
from ndrangheta.read_dot import sanitize_metanode

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
    def __init__(self, world: World, graph):
        self.w     = world
        self.graph = graph

        
    def describe_shipment(self, town: Town, loss: float, my_family: FamilyID):
        """
        Just a fancy print function for shipment movements.
        """
        town_name, is_hostile = town.name, town.family.id != my_family

        # print(f"shipment_family={my_family}, this family={town.family.id}")
        print(f"In node {town.id} lost {100*(1-loss):.2f}%")
        print("\tWas " + ("" if is_hostile else "not ") + "hostile")
        print(f"\tHold is {town.hold:.2f}")
        print("")


    def is_valid_shipment(self, start: TownID, end: TownID, ship: Shipment=None) -> bool:
        t1, t2 = self.w.Town(start), self.w.Town(end)
        self.check_is_valid_shipment_geographically(t1, t2)
        self.check_is_valid_shipment_drug_wise(t1, t2, ship)

        return True

    
    def check_is_valid_shipment_geographically(self, t1: Town, t2: Town):
        if t1.family != t2.family:
            raise ShipmentError(f"Destination is a place not owned by family {t1.family.id}")

        
    def check_is_valid_shipment_drug_wise(self, t1: Town, _: Town, ship):
        if t1.drugs < ship.initial_kgs:
            raise ShipmentError(f"Wanted to send {ship.initial_kgs}kg, "
                                f"but only {t1.drugs} are available in {t1}")
        if ship.initial_kgs <= 0:
            raise ShipmentError(f"Zero or below kgs of drugs scheduled ({ship.initial_kgs})")

    
    def move_single(self, start_id: TownID, end_id: TownID, ship: Shipment) -> bool:
        """
        Move a package from a city to the other.
        """
        
        if end_id not in self.graph.adj[start_id]:
            raise ShipmentError(f"Node {start_id} not adjacent to node {end_id}")

        start, end = self.w.Town(start_id), self.w.Town(end_id)

        remaining_percent = end.transit_shipment(ship)
        
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

        print()
        print("*"*12)
        print(f"SHIPMENT: {start} to {end}, {ship.kgs}kg\n")
        
        town = self.w.Town(start)
        town.mail_shipment(ship)
        
        from_node = path[0]
        
        for town_id in path[1:]: #NB: la prima iter sarà move(start, start)!
            ok = self.move_single(from_node, town_id, ship)

            if not ok:
                print(f"Failed to deliver, package captured in {town_id}! Lost {ship.kgs}kg!")
                print("*"*12)
                self.w.Town(town_id).capture_shipment(ship)
                return 0
            
            from_node = town_id

        town = self.w.Town(end)
        old_hold = town.hold
        # new_hold = town.change_hold(ship.loss_percent())

        town.receive_shipment(ship)  
            
        print(
            f"Arrived at destination ({town.id}) "
            f"with {ship.kgs:.2f}kg, "
            f"lost {ship.loss_absolute():.2f}kg on the way.\n"
            f"Hold at {town.id} changed from {old_hold:.2f} to {town.hold:.2f}"
            f"(difference: {town.hold-old_hold:.2f})" 
        )
        print("*"*12)
        
        return ship.kgs

    def automatic_path(self, start_id: TownID, end_id: TownID,
                       strategy: Callable[[TownID, TownID, Any], float]) -> List[TownID]:

        start, end = self.w.Town(start_id), self.w.Town(end_id)
        self.check_is_valid_shipment_geographically(start, end)
            
        return nx.dijkstra_path(
            self.graph,
            start_id, end_id,
            weight=lambda n1, n2, e: strategy(
                start.family.id,
                n1, n2, e
            )
        )
    
        
    def safest_path_heuristic(self, my_family: FamilyID, _, end_id: TownID, __):
        t2 = self.w.Town(end_id)
        
        if t2.family.id != my_family:
            # Safe = evita a tutti i costi, a meno che non sia
            # inevitabile, un nodo di una famiglia avversaria
            return len(Town.TOWNS) * t2.hold
        
        return 1 - t2.hold
    

    def send_shipment_safest(self, 
            start: TownID,
            end: TownID,
            ship: Shipment) -> int:

        return self.send_shipment_manual(
            start, end, ship,
            self.automatic_path(start, end, self.safest_path_heuristic)
        )

    
    def best_expected_path_heuristic(self, my_family, __, t_id2, _):
        t2 = self.w.Town(t_id2)

        if t2.family.id != my_family:
            # E[multiplier in A->B] = E[Uniform(hold(B), 1)]
            # = (1 + hold(B)) / 2
            return (1 + t2.hold) / 2
        
        # hold = 1   => v = 0 => impossible to pass
        # hold = 0.5 => v = 1 => no risk passing
        return 2 * (1 - t2.hold)                

    
    def expected_multiplier_path(self, path: List, my_family: FamilyID, strategy: Callable) -> float:
        m = 1
        for tid in path[1:]:
            t = self.w.Town(tid)
            if t.family.id != my_family:
                m *= 2*(1 - t.hold)
            else:
                m *= (1 + t.hold) / 2
        return m
    
# =========================================================== #

class DrugError(Exception): pass

class Narcos():
    def __init__(self, world: World):
        self.world = world
        
    def get_price(self, kgs=1):
        return 60_000 * kgs # 60_000$ = 1Kg
    
    def sell_drugs(self, kgs: int, family: Family, dest: TownID) -> Tuple[Callable, Any]:
        """
        Buying drugs from narcos is a 2-step operation.
        
        Firstly, narcos gets all the money (sell_drugs()); then, at the next turn,
        the family will be delivered the drugs (deliver_drugs()).
        """
        if self.world.Town(dest).family.id != family.id:
            raise ShipmentError("Destination is of a different family!")
        
        money_needed = int(kgs * self.get_price())

        if family.money < money_needed:
            raise DrugError(f"{money_needed:n}$ needed, but you only have {family.money:n}")

        family.money -= money_needed

        return Schedule(self.deliver_drugs, In(turn=1), kgs, family, dest)

    def deliver_drugs(self, kgs, family, dest):
        self.world.Town(dest).receive_shipment(Shipment(kgs, 80_000, family))
        
    def sell_drugs_immediately(self, kgs: int, family: Family, dest: TownID):
        return self.sell_drugs(kgs, family, dest)()
        
# =========================================================== #
    
class Ask():
    @staticmethod
    def confirm():
        print("Confirm? (y/N)", end=" ")
        answer = input("... ")
        return answer == "y"

        
# =========================================================== #
from ndrangheta.read_dot import load_graph

class AI:
    def __init__(self, world: World, simulator: "Simulator"):
        self.s = simulator
        self.w = world
        
    def decide_shipments(self, family_id):
        fam  = self.w.Family(family_id)
        reqs = self.sort_ai_cities_proposals(family_id)
        
        if family_id == -1 or len(reqs) == 0:
            return

        print(f"TURN: AI {family_id}")
        #Provo tutte le richieste; la prima che posso esaudire, la esaudisco;
        #do priorità a quelle più urgenti.
        #Per ora, unica opzione è comprare dai narcos
        sorted_reqs = reqs

        print("REQUESTS:")
        for r in sorted_reqs:
            print("\t", r)
            
        for r in sorted_reqs:
            cost = self.s.ask_drug_price_to_narcos(r.kgs)
            
            if fam.money > cost:
                print("CHOSEN: ", r)
                self.s.buy_from_narcos(family_id, r.kgs, immediate=True)

                self.s.router.send_shipment_safest(
                    fam.capital, r.author,
                    Shipment(r.kgs, 80_000, fam.id)
                )

            
    def sort_ai_cities_proposals(self, family_id: FamilyID):
        """
        Sorts all the proposals of every city of a family.
        """
        fam = self.w.Family(family_id)
        
        proposals = list()
        for p in fam.gather_requests_from_cities():
            proposals.append(
                self.__adjust_req_proposal_according_to_distance(fam, p)
            )

        return sorted(proposals, key=lambda x: x.needed_before)

    
    def __adjust_req_proposal_according_to_distance(self, fam: Family, req: Any):
        """ 
        Increases the amount on drugs requested by a local family 
        according to the expected loss on the path of the shipment.
        """
        if not isinstance(req, Request):
            return req        
        
        path = self.s.router.automatic_path(
            fam.capital, req.author, self.s.router.safest_path_heuristic
        )
        mult = self.s.router.expected_multiplier_path(
            path, fam.id, self.s.router.safest_path_heuristic
        )
        req.kgs *= (2 - mult)

        return req


class Simulator:
    def __init__(self, world: World, graph):
        self.world  = world
        self.router = Routing(world, graph)
        self.narcos = Narcos(world)
        
        self.player_id, self.player = 0, self.world.Family(0)

        self.ai = AI(self.world, self)
        self.turn = 0

    def update_graph(self):
        for tid, t in self.world.towns.items():
            print(t.__dict__.items())
            nx.set_node_attributes(
                self.router.graph,
                {tid:
                 ({k:v for k,v in t.__dict__.items() if k not in ["local_family"]} |
                  {"family": t.family.id})}   
            )
        
    def save_graph(self, fpath):
        self.update_graph()
        show(self.router.graph, False, True, fpath="web/map.svg")

    def show_graph(self):
        self.update_graph()
        show(self.router.graph)

    # =========================================================== #
    
    def advance_time(self, turns=1):
        for _ in range(turns):
            for _, town in self.world.towns.items():
                town.advance_turn()

            # Every turn follows a random order of execution
            for family_id in shuffle(list(self.world.families)):
                self.ai_family_turn(family_id)

            self.turn += 1

        
    def ai_family_turn(self, family_id: FamilyID):
        if family_id != self.player_id:
            self.ai.decide_shipments(family_id)
            return

        # if human player:
        for op in self.player.scheduled_operations:
            op()
        self.player.scheduled_operations = list()


    def buy_from_narcos(self, family_id, kgs, immediate=False) -> Union[Tuple[Callable, KG], None]:
        family = self.world.Family(family_id)
        dest   = family.capital

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
        self.world.Family(player_id).change_tax_in(city, amount)

        
    def declare_war_schedule(self, player_id: FamilyID, tid1: TownID, tid2: TownID):
        t1, t2 = self.world.Town(tid1), self.world.Town(tid2)

        if t1.family == t2.family:
            raise WarError("Can't declare war between two friendly city!")
        if t2.hold > 0.7:
            raise WarError("Can't declare war if hold in defender is >0.7!")
        if t1.family.id != player_id:
            raise WarError("Can't control non-owned cities!")
        # TODO: controlla che città siano dirimpettaie 

        t1.family.scheduled_operations.append(
            Schedule(self.declare_war, In(turn=1),
                     player_id, tid1, tid2)
        )
    
    def declare_war(self, player_id: FamilyID, tid1: TownID, tid2: TownID):
        t1, t2 = self.world.Town(tid1), self.world.Town(tid2)

        if t1.family == t2.family:
            raise WarError("Can't declare war between two friendly city!")
        if t2.hold > 0.7:
            raise WarError("Can't declare war if hold in defender is >0.7!")
        if t1.family.id != player_id:
            raise WarError("Can't control non-owned cities!")
        # TODO: controlla che città siano dirimpettaie 

        
        def defense_factor(t):
            return 2 ** ((t.hold - 0.6) * 10)
        
        atk_val = t1.local_family.soldiers * t1.local_family.leader
        def_val = t2.local_family.soldiers * t2.local_family.leader * defense_factor(t2)

        print(atk_val, def_val)
        
        if atk_val > def_val:
            print(f"City {t2.id} conquered!")
            
            if t2.is_capital:
                # BUG: cancellazione comporta qualche side effect?
                del self.world.families[t2.family.id]
                
                towns = [t for t in self.world.towns.values() if t.family==t2.family]

                for t in towns:
                    if t == t2:
                        continue
                    # new_family
                    fam_id = self.world.new_id_for_family()
                    f = Family(fam_id, str(fam_id), sanitize_metanode({"family": fam_id}))
                    t.change_ownership(f)
                    t.change_hold(loss_percent=100)
                    t.is_capital = True
                    f.capital = t.id
                    
            t2.change_ownership(t1.family)

            t1.local_family.soldiers = (
                round((atk_val - def_val) / t1.local_family.leader)
            )
            t2.local_family.soldiers = (
                random.randint(0, t2.local_family.soldiers // 4)
            )
            
            t1.local_family.variate_leader(+0.5)
            t2.local_family.variate_leader(1, override=True)

            t2.hold = 0.7
            t1.hold += 0.08

            t1.family.drugs += t2.drugs
            
            
        else:
            t1.local_family.variate_leader(-1)
            t2.local_family.variate_leader(+1)

            t2.hold = 0.7
            t1.hold -= 0.08

            t2.local_family.soldiers = (
                round((def_val - atk_val) / t2.local_family.leader)
            )
            t1.local_family.soldiers = (
                random.randint(0, t1.local_family.soldiers // 4)
            )

            
# =========================================================== #

def play():
    import readline

    # sim = Simulator(load_graph("tests/dots/fun.dot"))
    world, graph = load_graph("ndrangheta/example.dot")
    sim = Simulator(world, graph)
    player_id = 0
    player    = world.Family(player_id)
    
    while True:
        try:
            player.stats(turn=sim.turn)

            s = input("λ) ").split(" ")

            if s[0] == "save":
                sim.save_graph(0)
                
            if s[0] == "show":
                sim.show_graph()

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
                    operation = sim.buy_from_narcos(player_id, amount)
                    player.scheduled_operations.append(operation)
                    
                    
            if s[0] == "send": #path
                from_, to, amount = int(s[1]), int(s[2]), int(s[3])
                ship = Shipment(amount, 80_000, world.Town(from_).family.id)
                    
                if sim.router.is_valid_shipment(from_, to, ship):
                    player.scheduled_operations.append(
                        Schedule(sim.send_shipment, In(turn=1), from_, to, ship)
                    )


            if s[0] == "list":
                world.print_cities(player_id)

            if s[0].startswith("req"):
                if len(s) == 2:
                    f_id = int(s[1])
                else:
                    f_id = player.id

                for r in player.gather_requests_from_cities():
                    print(r)

            if s[0] == "w":
                t1, t2 = int(s[1]), int(s[2])
                sim.declare_war_schedule(player_id, t1, t2)
                
            if s[0] == "q":
                break

            if s[0] == "d":
                breakpoint()

            if s[0] == "cp":
                player_id = int(s[1])
                # player_id = Family.next(player_id)
                player = world.Family(player_id)
                
            if s[0] == "t":
                t = int(s[1]) if len(s) == 2 else 1
                sim.advance_time(turns=t)
                
        except Exception as e:
            import traceback
            
            traceback.print_exc()
            continue
