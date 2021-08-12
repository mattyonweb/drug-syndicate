from typing import *

class World:
    def __init__(self):
        self.towns = dict()
        self.families = dict()
        self.highest_fid: "FamilyID" = 0
        
    def add_town(self, t: "Town"):
        self.towns[t.id] = t

    def add_family(self, f: "Family"):
        self.families[f.id] = f
        self.highest_fid = max(f.id, self.highest_fid)

    def Family(self, f_id: "FamilyID"):
        return self.families[f_id]

    def Town(self, t_id: "TownID"):
        return self.towns[t_id]

    def towns_of_family(self, f_id: "FamilyID"):
        return [t for t in self.towns.values() if t.family.id == f_id]

    def print_cities(self, family_id, exclude_others=False):
        for tid, t in self.towns.items():
            if exclude_others and t.family.id != family_id:
                continue

            print(t.str_stats(t.family.id != family_id))

    def new_id_for_family(self):
        return self.highest_fid + 1
    
