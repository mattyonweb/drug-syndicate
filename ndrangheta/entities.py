from typing import *

import random

# =========================================================== #

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
                 name=None, hold=None):
        
        assert(town_id not in Town.TOWNS)
        
        self.id:     TownID   = town_id
        self.family: FamilyID = family_id

        self.name:   str      = Town.NAMES[self.id]
        self.hold = 0.5 + random.random() / 2 if hold is None else hold
        
        Town.TOWNS[self.id] = self

        
    @staticmethod
    def get(id: TownID):
        return Town.TOWNS[id]
