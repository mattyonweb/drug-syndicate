from typing import *
from dataclasses import dataclass

# from ndrangheta.utils import cap, montecarlo, Schedule, When, In, Every
from ndrangheta.utils import *

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
        if id is None:
            id = max(Family.FAMILIES) + 1
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

    @staticmethod
    def next(id: FamilyID):
        return (list(Family.FAMILIES).index(id) + 1) % len(Family.FAMILIES)

    
    def stats(self, turn=None):
        if turn is None:
            print(f"======== Player {self.id} - {self.money:n}€ - {self.drugs:.2f}kg ========")
        else:
            print(f"T{turn} ======== Player {self.id} - {self.money:n}€ - {self.drugs:.2f}kg ========")
        
    def local_asks_for_drug(self, request: Request):
        self.drug_requests.append(request)
        
    def cancel_request(self, author: "TownID"):
        self.drug_requests = del_satisfying(
            self.drug_requests,
            lambda r: r.author == author
        )

    def receive_tax(self, from_: "TownID", money):
        # TODO: from_ usabile in futuro per AI
        self.money += money
        
    def change_tax_in(self, town_id: "TownID", new_tax_rate: float):
        my_assert(
            Town.get(town_id).family.id == self.id,
            ViolationError("Attempted to change taxes to not owned city")
        )

        my_assert(
            0.0 <= new_tax_rate <= 1.0,
            ValueError__("Tax rate not between 0.0 and 1.0 (or 0 and 100%)")
        )
        
        Town.get(town_id).local_family.change_tax_rate(new_tax_rate)
    
        
class Police(Family):
    def local_asks_for_drug(self, request: Request):
        print("SHOULND READ ME")

    

class LocalFamily:
    def __init__(self, parent: Family, town: "Town", soldiers:int, leader: int):
        self.parent = parent
        self.town   = town
        
        self.regulars = 7 #7 regulars user every 1000 (once a day)
        self.saltuary = 14 #14 non-regular users every 1000 (once a month)
        self.regular_dose: KG = 0.0003 #0.0003 kg => 0.3 grams
        self.salutar_dose: KG = 0.0001

        self.money = 0
        self.drug_cost_per_kg = 80_000 # TODO deve essere fornito dal package/master family
        self.tax: float = 0.5 # TODO

        self.soldiers = soldiers
        self.leader   = leader
        
        self.sent_request = False
        self.futures = [Schedule(self.pay_taxes, Every(turn=7, countdown=7))]
        self.turn = 0


    def change_tax_rate(self, new_tax: float):
        assert(new_tax >= 0)
        self.tax = new_tax

    def pay_taxes(self):
        tax_money = int(self.tax * self.money)
        self.money -= tax_money
        self.parent.receive_tax(self.town.id, tax_money)

    # =========================================================== #
    
    def variate_leader(self, val, override=False):
        if override:
            self.leader = val
        else:
            self.leader += val

    # =========================================================== #
            
    def avg_daily_regular_dose(self) -> KG:
        #TODO: add randomness on number of self.regulars
        return self.regular_dose * self.regulars * (self.town.population / 1000)

    # def avg_monthly_saltuar_dose(self) -> KG:
    #     return self.salutar_dose * self.saltuary * (self.town.population / 1000)

    def avg_daily_saltuar_dose(self) -> KG:
        return (self.salutar_dose * self.saltuary * (self.town.population / 1000)) / 30
    
    def estimate_monthly_consumption(self) -> KG:
        return int( #30 = 30 days
            30 * self.avg_daily_regular_dose() + 30 * self.avg_daily_saltuar_dose()
        ) + 5*self.avg_daily_regular_dose() # just for safety

    def estimate_daily_consumption(self):
        return self.avg_daily_regular_dose() + self.avg_daily_saltuar_dose()
    
    def estimate_remaining_days(self):
        return self.town.drugs / self.estimate_daily_consumption()

    
    def sell_daily_doses(self) -> KG:
        # TODO: this function does two things simulatneously,
        # sell doses and change town hold. Safe to do both here?
        remaining_days = self.estimate_remaining_days()

        # if self.town.family.id != 0: #BUG: wtf?
        #     print(self.town.id, end=" ")
            
        if remaining_days > 5:
            sold_kgs = self.estimate_daily_consumption()
            
        elif remaining_days > 1:
            self.town.hold = cap(self.town.hold - 0.01, 0.5, 1)
            sold_kgs = max(
                0.5 * (self.avg_daily_regular_dose() + self.avg_daily_saltuar_dose()),
                self.town.drugs
            )
            
        else:
            self.town.hold = cap(self.town.hold - 0.05, 0.5, 1)
            sold_kgs = 0

        self.money += self.drug_cost_per_kg * sold_kgs
        return sold_kgs

    
    def receive_shipment(self, ship: "Shipment"):
        """
        To be called from Town() when Town() is destination of a shipment.
        """
        # self.sent_request = False
        self.drug_cost_per_kg = ship.price_per_kg
        self.update_family_about_local_drug_situation()

        
    def current_drug_situation(self) -> Request:
        """
        Returns the current situation, drug-wise, of the city
        """
        return Request(
            self.estimate_monthly_consumption(),
            author=self.town.id,
            needed_before=self.estimate_remaining_days()
        )

    
    def is_drug_situation_critical(self, req: Request):
        return req.needed_before < 5

    
    def update_family_about_local_drug_situation(self, req: Request=None):
        """
        If the drug-situation is critical (eg. less than 5 days before running
        out of drugs) informs the main family.

        If we were waiting for a package but suddenly we don't need it anymore 
        (eg. because of stolen package) cancel the previous request.
        """
        if req is None:
            req = self.current_drug_situation()
            
        # If waiting for a package from master family...
        if self.sent_request:
            # ...but somehow (eg. stolen a package from opponent) you
            # dont need it anymore, call it off
            if not self.is_drug_situation_critical(req):
                self.parent.cancel_request(author=self.town.id)
                self.sent_request = False

            # TODO: dovresti mettere la condizione: se rem_days < 5:
            # cancella la vecchia richiesta dalla master family,
            # aggiungi nuova richiesta con statistiche aggiornate
            # (quanta te ne serve, entro quanto, ecc)
            return
        
        if self.is_drug_situation_critical(req):
            self.parent.local_asks_for_drug(req)
            self.sent_request = True

    # =========================================================== #

    def advance_turn(self):
        self.turn += 1

        # Scheduled activites executer
        done = list()
        for i, task in enumerate(self.futures):
            if isinstance(task.when, Every):
                if task.when.countdown == 0:
                    print(task)
                    task()
                    task.when.countdown = task.when.turn
                else:
                    task.when.countdown -= 1
                    
            elif isinstance(task.when, In):
                if task.when.turn == 0:
                    print(task)
                    task()
                    done.append(i)
                else:
                    task.when.turn -= 1
                    
        # removes done tasks
        for i in done[::-1]:
            del self.futures[i]
              
        self.update_family_about_local_drug_situation()

# =========================================================== #

TownID = int

class Town():
    TOWNS: Dict[TownID, "Town"] = dict()
    
    # def __init__(self, town_id: TownID, family_id: FamilyID, **kwargs):        
    def __init__(self, town_id: TownID, family: Family, **kwargs):        
        assert(town_id not in Town.TOWNS)
        
        self.id:     TownID = town_id
        self.family: Family = family
        self.is_capital = kwargs["capital"]
        
        self.name: str   = ""
        self.hold: float = (
            random.uniform(0.5, 1)
            if kwargs["hold"] is None
            else kwargs["hold"]
        )
        self.population = (
            kwargs["pop"] if kwargs["pop"] is not None
            else random.randint(1, 100) * 1000
        )

        self.local_family = LocalFamily(
            parent=self.family,
            town=self,
            soldiers=min(kwargs["soldiers"], self.population // 1000),
            leader=kwargs["leader"]
        )
        self.drugs = kwargs["drugs"] if self.family.id != -1 else 0 
        
        Town.TOWNS[self.id] = self

        
    @staticmethod
    def get(id: TownID):
        return Town.TOWNS[id]

    
    @staticmethod
    def get_of_family(id: FamilyID):
        return [t for t in Town.TOWNS.values() if t.family.id == id]


    def str_stats(self, am_hostile) -> str:
        s = ""
        s += f"({self.id})\t - Family: {self.family.id} - Hold: {self.hold:.2f} "
        s += f" - Pop: {self.population:n} "

        if not am_hostile:
            s += f"- Drugs: {self.drugs:.2f}kg "
            s += f"- Taxes: {100*self.local_family.tax:.0f}% "
            s += f"- Army: {self.local_family.soldiers} ({self.local_family.leader}) "
            
        # if self.id == self.family.capital:
        if self.is_capital:
            s += f"- CAPITAL "

        return s

    
    @staticmethod
    def print_cities(family_id, exclude_others=False):
        for tid in Town.TOWNS:
            t = Town.get(tid)

            if exclude_others and t.family.id != family_id:
                continue

            print(t.str_stats(t.family.id != family_id))

            
    def change_family(self, new_family: Family):
        self.family = new_family
        self.local_family.parent = Family.FAMILIES[self.family.id]
        if self.is_capital:
            self.is_capital = False
        #TODO: e se diventa una città indipendente (ie. Fam.FAM[id] non esiste)?

        
    def change_hold(self, loss_percent: float, dry_run=False) -> float:
        """
        Changes hold after receiving a package.
        """
        if loss_percent <= 5:
            hold = cap(self.hold * 1.12, 0.5, 1)
        elif loss_percent <= 10:
            hold = cap(self.hold * random.uniform(0.95, 1.05), 0.5, 1)
        else:
            hold = cap(self.hold * (0.95 - (loss_percent-10)/100), 0.5, 1)

        if not dry_run:
            self.hold = hold
            
        return hold


    def variate_drugs(self, amount: int, reason:str=""):
        """
        Change amount of drugs in a city by a delta.
        """
        self.drugs += amount
        
        assert self.drugs >= 0, (f"Drugs under 0 in city {self.id}; "
                                 f"was {self.drugs - amount}, removed {amount}"
                                 f" - reason: {reason}")

        # TODO: fatto += a destinazione, ma fatto anche -= alla partenza?
        self.family.drugs += amount
        
        
    def mail_shipment(self, ship: "Shipment"):
        """
        Call this on the starting city of a shipment.
        """
        self.variate_drugs(- ship.initial_kgs, reason="Started shipment")

        
    def transit_shipment(self, ship: "Shipment") -> float:
        """
        Call this if shipment if transiting through this city.
        Returns the percenteage loss.
        """
        if self.family.id != ship.from_family:
            # hold = 1    => prob = 1
            # hold = 0.75 => prob = 0.5
            # hold = 0.50 => prob = 0
            if not montecarlo(self.hold - (1 - self.hold)):
                self.capture_shipment(ship)
                return 0

            return 1.0
        
        return random.uniform((1 + self.hold) / 2, 1)
 
        
    def receive_shipment(self, ship: "Shipment"):
        self.change_hold(ship.loss_percent())
        self.variate_drugs(ship.kgs, reason="ship reached destination")        
        self.local_family.receive_shipment(ship)
                                           

    def capture_shipment(self, ship: "Shipment"):
        self.variate_drugs(ship.kgs, reason="ship captured!")
        self.local_family.update_family_about_local_drug_situation()
        # TODO: ci starebbe tipo che aumenta (o diminuisce?) la hold?

    # =========================================================== #
    
    def estimate_future_hold(self, ship_multiplier=None) -> float:
        # TODO: tenere conto di possibilità di guerra se hold < 70
        h = 0
        if ship_multiplier is not None:
            h = self.change_hold(100 * (1 - ship_multiplier), dry_run=True) - self.hold
        if h == 0 and self.hold == 0.5:
            return -1
        if h == 0 and self.hold == 1:
            return 1
        return h

    def estimate_other_params(self):
        return cap(
            (self.local_family.estimate_remaining_days() - 1) / 5,
            0, 1
        )

    def evaluate_situation(self, ship_multiplier=None):
        return (
            0.8 * self.estimate_future_hold(ship_multiplier) +
            0.2 * self.estimate_other_params()
        )
    
    # =========================================================== #
    
    def consume_drugs_single_day(self) -> float:
        sold_kgs = self.local_family.sell_daily_doses()
        self.variate_drugs(- sold_kgs,
                           reason="daily drug use")
    def ai_proposals(self) -> Union[None, List[Request]]:
        reqs = [self.local_family.current_drug_situation()]
        return reqs
        
    def advance_turn(self):
        if self.family.id == -1:
            pass # is police town
        else:
            self.consume_drugs_single_day() #TODO perchè qui?!
            self.local_family.advance_turn()
