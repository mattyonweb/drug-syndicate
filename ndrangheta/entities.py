from typing import *
from dataclasses import dataclass

from ndrangheta.utils import cap, montecarlo, Schedule, When, In, Every

import random

KG = float

@dataclass
class Request:
    kgs: float
    author: "TownID"
    needed_before: int = 1
 

# =========================================================== #

FamilyID = int

class Family():
    FAMILIES: Dict[FamilyID, "Family"] = dict()

    def __init__(self, id: FamilyID, name):
        assert(id not in Family.FAMILIES)
        
        self.name = name
        self.id = id
        self.capital: "TownID" = None
        
        self.money: int = 1_000_000
        self.drugs: int = 0
        
        self.drug_requests: List[Tuple[FamilyID, float]] = list()
        self.scheduled_operations: List[Tuple] = list()
        
        Family.FAMILIES[self.id] = self

        
    @staticmethod
    def get(id: FamilyID):
        return Family.FAMILIES[id]

    def stats(self, turn=None):
        if turn is None:
            print(f"======== Player {self.id} - {self.money:n}€ - {self.drugs}kg ========")
        else:
            print(f"T{turn} ======== Player {self.id} - {self.money:n}€ - {self.drugs}kg ========")
        
    def local_asks_for_drug(self, request: Request):
        self.drug_requests.append(request)

    def receive_tax(self, from_: "TownID", money):
        # TODO: from_ usabile in futuro per AI
        self.money += money
        
    def change_tax_in(self, town_id: "TownID", new_tax_rate: int):
        Town.get(town_id).local_family.change_tax_rate(new_tax_rate)
    
        
class Police(Family):
    def local_asks_for_drug(self, request: Request):
        print("SHOULND READ ME")

    

class LocalFamily:
    def __init__(self, parent: Family, town: "Town"):
        self.parent = parent
        self.town   = town
        
        self.regulars = 7 #7 regulars user every 1000 (once a day)
        self.saltuary = 14 #14 non-regular users every 1000 (once a month)
        self.regular_dose: KG = 0.0003 #0.0003 kg => 0.3 grams
        self.salutar_dose: KG = 0.0001

        self.money = 0
        self.drug_cost_per_kg = 80_000 # TODO deve essere fornito dal package/master family
        self.tax: float = 0.5 # TODO
        
        self.sent_request = False
        self.futures = [Schedule(self.pay_taxes, Every(turn=7, countdown=7))]
        self.turn = 0

    def change_tax_rate(self, new_tax: float):
        assert(new_tax >= 0)
        self.tax = new_tax

    def pay_taxes(self):
        tax_money = self.tax * self.money
        self.money -= tax_money
        self.parent.receive_tax(self.town.id, tax_money)
        
    def avg_daily_regular_dose(self) -> KG:
        #TODO: add randomness on number of self.regulars
        return self.regular_dose * self.regulars * (self.town.population / 1000)

    def avg_monthly_saltuar_dose(self) -> KG:
        return self.salutar_dose * self.saltuary * (self.town.population / 1000)

    def estimate_monthly_consumption(self) -> KG:
        return int( #30 = 30 days
            30 * self.avg_daily_regular_dose() + self.avg_monthly_saltuar_dose()
        ) + 2 * self.avg_daily_regular_dose() # just for safety

    def estimate_remaining_days(self):
        return self.town.drugs / (self.estimate_monthly_consumption() / 30)

    
    def sell_daily_doses(self) -> KG:
        # TODO: this function does two things simulatneously,
        # sell doses and change town hold. Safe to do both here?
        remaining_days = self.estimate_remaining_days()

        if remaining_days > 5:
            sold_kgs = self.avg_daily_regular_dose() + self.avg_monthly_saltuar_dose() / 30
        elif remaining_days > 1:
            self.town.hold = cap(self.town.hold - 0.01, 0.5, 1)
            sold_kgs = 0.5 * (self.avg_daily_regular_dose() + self.avg_monthly_saltuar_dose() / 30)
        else:
            self.town.hold = cap(self.town.hold - 0.05, 0.5, 1)
            sold_kgs = 0

        self.money += self.drug_cost_per_kg * sold_kgs
        return sold_kgs

    
    def receive_shipment(self, ship: "Shipment"):
        """
        To be called from Town() when Town() is destination of a shipment.
        """
        self.sent_request = False
        self.drug_cost_per_kg = ship.price_per_kg

        
    def evaluate_need_for_drug(self):
        if self.sent_request:
            # If already sent a request, dont do it again
            return
        
        remaining_days = self.estimate_remaining_days()
        
        if remaining_days < 5:
            self.parent.local_asks_for_drug(
                Request(
                    self.estimate_monthly_consumption(),
                    author=self.town.id,
                    needed_before=remaining_days
                )
            )

            self.sent_request = True
            

    def advance_turn(self):
        self.turn += 1

        # Scheduled activites executer
        done = list()
        for i, task in enumerate(self.futures):
            if isinstance(task.when, Every):
                if task.when.countdown == 0:
                    task()
                    task.when.countdown = task.when.turn
                else:
                    task.when.countdown -= 1
                    
            elif isinstance(task.when, In):
                if task.when.turn == 0:
                    task()
                    done.append(i)
                else:
                    task.when.turn -= 1
        # removes done tasks
        for i in done[::-1]:
            del self.futures[i]
            
                    
        self.evaluate_need_for_drug()

# =========================================================== #

TownID = int

class Town():
    NAMES = open("ndrangheta/calabria.txt", "r").readlines()
    TOWNS: Dict[TownID, "Town"] = dict()
    
    def __init__(self, town_id: TownID, family_id: FamilyID, **kwargs):        
        assert(town_id not in Town.TOWNS)
        
        self.id:     TownID   = town_id
        self.family: FamilyID = family_id
        
        self.name: str   = Town.NAMES[self.id]
        self.hold: float = (
            random.uniform(0.5, 1)
            if kwargs["hold"] is None
            else kwargs["hold"]
        )
        self.population = (
            kwargs["pop"] if kwargs["pop"] is not None
            else random.randint(1, 100) * 1000
        )

        self.local_family = LocalFamily(Family.get(self.family), self)        
        self.drugs = kwargs["drugs"] if self.family != -1 else 0 
        
        Town.TOWNS[self.id] = self

        
    @staticmethod
    def get(id: TownID):
        return Town.TOWNS[id]

    
    @staticmethod
    def get_of_family(id: FamilyID):
        return [t for t in Town.TOWNS.values() if t.family == id]

    
    @staticmethod
    def print_cities(family_id, exclude_others=False):
        for tid in Town.TOWNS:
            t = Town.get(tid)

            if exclude_others and t.family != family_id:
                continue
            
            print(f"({t.id})\t - Family: {t.family} - Hold: {t.hold:.2f}", end=" ")
            if t.family == family_id:
                print(f"- Drugs: {t.drugs:.2f}kg", end=" ")
            if tid == Family.get(t.family).capital:
                print(f"- CAPITAL", end=" ")

            print()

                
    def change_hold(self, loss_percent: float) -> float:
        if loss_percent <= 5:
            self.hold = cap(self.hold * 1.12, 0.5, 1)
        elif loss_percent <= 10:
            self.hold = cap(self.hold * random.uniform(0.95, 1.05), 0.5, 1)
        else:
            self.hold = cap(self.hold * (0.95 - (loss_percent-10)/100), 0.5, 1)

        return self.hold


    def variate_drugs(self, amount: int):
        """
        Change amount of drugs in a city by a delta.
        """
        self.drugs += amount
        
        assert self.drugs >= 0, (f"Drugs under 0 in city {self.id}; "
                                 f"was {self.drugs + amount}, removed {amount}")

        Family.get(self.family).drugs += amount
        
        
    def mail_shipment(self, ship: "Shipment"):
        """
        Call this on the starting city of a shipment.
        """
        self.variate_drugs(- ship.initial_kgs)

        
    def transit_shipment(self, ship: "Shipment") -> float:
        """
        Call this if shipment if transiting through this city.
        Returns the percenteage loss.
        """
        if self.family != ship.from_family:
            # hold = 1    => prob = 1
            # hold = 0.75 => prob = 0.5
            # hold = 0.50 => prob = 0
            if not montecarlo(self.hold - (1 - self.hold)):
                # self.describe_shipment(town, 0, my_family)
                # ship.displace(0, town)
                self.capture_shipment(ship)
                return 0
            
            # self.describe_shipment(town, 1, my_family)
            # ship.displace(1, town)
            return 1.0
        
        return random.uniform((1 + self.hold) / 2, 1)
        # ship.displace(loss, town)
        # self.describe_shipment(town, loss, my_family)
 
        
    def receive_shipment(self, ship: "Shipment"):
        self.variate_drugs(ship.kgs)        
        self.local_family.receive_shipment(ship)
                                           

    def capture_shipment(self, ship: "Shipment"):
        self.variate_drugs(ship.kgs)
        # TODO: ci starebbe tipo che aumenta (o diminuisce?) la hold?

    # =========================================================== #
    
    def consume_drugs_single_day(self):
        self.variate_drugs(- self.local_family.sell_daily_doses())
        
    def advance_turn(self):
        if self.family == -1:
            pass # is police town
        else:
            self.consume_drugs_single_day() #TODO perchè qui?!
            self.local_family.advance_turn()
