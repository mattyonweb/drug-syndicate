from typing import *
from dataclasses import dataclass

from ndrangheta.utils import cap

import random


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

        self.money: int = 1_000_000
        self.drugs: int = 0

        self.drug_requests: List[Tuple[FamilyID, float]] = list()
        
        Family.FAMILIES[self.id] = self

    @staticmethod
    def get(id: FamilyID):
        return Family.FAMILIES[id]

    def stats(self):
        print(f"======== Player {self.id} - {self.money:n}€ - {self.drugs}kg ========")

    def local_asks_for_drug(self, request: Request):
        self.drug_requests.append(request)


class LocalFamily:
    def __init__(self, parent: Family, town: "Town"):
        self.parent = parent
        self.town   = town
        
        self.regulars = 7 #7 regulars user every 1000 (once a day)
        self.saltuary = 14 #14 non-regular users every 1000 (once a month)
        self.regular_dose = 0.3 #0.3 grams
        self.salutar_dose = 0.1


    def avg_daily_regular_dose(self) -> int:
        #TODO: add randomness on number of self.regulars
        return self.regular_dose * self.regulars * (self.town.population / 1000)

    def avg_monthly_saltuar_dose(self) -> int:
        return self.salutar_dose * self.saltuary * (self.town.population / 1000)

    def estimate_monthly_consumption(self):
        return int( #30 = 30 days
            30 * self.avg_daily_regular_dose() + self.avg_monthly_saltuar_dose()
        ) + 2 * self.avg_daily_regular_dose() # just for safety

    def estimate_remaining_days(self):
        return self.town.drugs / (self.estimate_monthly_consumption() / 30)
        
    def sell_daily_doses(self):
        remaining_days = self.estimate_remaining_days()

        if remaining_days > 5:
            return self.avg_daily_regular_dose() + self.avg_monthly_saltuar_dose() / 30
        elif remaining_days > 1:
            self.town.hold = cap(self.town.hold - 0.01, 0.5, 1)
            return 0.5 * (self.avg_daily_regular_dose() + self.avg_monthly_saltuar_dose() / 30)
        else:
            self.town.hold = cap(self.town.hold - 0.05, 0.5, 1)
            return 0
    
    def evaluate_need_for_drug(self):
        remaining_days = self.estimate_remaining_days()
        
        if remaining_days < 5:
            self.parent.local_asks_for_drug(
                Request(
                    self.estimate_monthly_consumption(),
                    author=self.town.id,
                    needed_before=remaining_days
                )
            )
            
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
        
        self.drugs = kwargs["drugs"]
        
        Town.TOWNS[self.id] = self

        
    @staticmethod
    def get(id: TownID):
        return Town.TOWNS[id]

    
    @staticmethod
    def print_cities(family_id):
        for tid in Town.TOWNS:
            t = Town.get(tid)
            
            print(f"({t.id})\t - Family: {t.family} - Hold: {t.hold}", end=" ")
            if t.family == family_id:
                print(f"- Drugs: {t.drugs}kg", end=" ")

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

        
    def mail_shipment(self, ship: "Shipment"):
        """
        Call this on the starting city of a shipment.
        """
        self.variate_drugs(- ship.initial_kgs)

        
    def receive_shipment(self, ship: "Shipment", family_id: FamilyID,
                         retail_multiplier=1):
        
        self.variate_drugs(ship.kgs)
        # TODO: qui ci sarà da verificare contratti e simili
        # family = Family.get(family_id)
        # family.money += ship.costed * retail_multiplier
        

    # =========================================================== #
    
    def consume_drugs_single_day(self):
        # self.variate_drugs(- (self.loc avg_daily_regular_dose() + self.avg_monthly_saltuar_dose()/30))
        self.variate_drugs(- self.local_family.sell_daily_doses())
        
    def advance_turn(self):
        self.consume_drugs_single_day()
        self.local_family.evaluate_need_for_drug()
