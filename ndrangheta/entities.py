from typing import *

from ndrangheta.utils import cap

import random

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

        Family.FAMILIES[self.id] = self

    @staticmethod
    def get(id: FamilyID):
        return Family.FAMILIES[id]

    def stats(self):
        print(f"======== Player {self.id} - {self.money:n}€ - {self.drugs}kg ========")

# =========================================================== #

TownID = int

class Town():
    NAMES = open("ndrangheta/calabria.txt", "r").readlines()
    TOWNS = dict()
    
    def __init__(self, town_id: TownID, family_id: FamilyID,
                 name=None, hold=None):
        
        assert(town_id not in Town.TOWNS)
        
        self.id:     TownID   = town_id
        self.family: FamilyID = family_id

        self.name:   str      = Town.NAMES[self.id]
        self.hold = 0.5 + random.random() / 2 if hold is None else hold

        self.drugs = 0
        
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


    def add_drugs(self, amount: int):
        self.drugs += amount
