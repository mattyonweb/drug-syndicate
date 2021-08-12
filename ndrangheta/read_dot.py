from typing import *
import networkx as nx
import matplotlib.pyplot as plt

from ndrangheta.config import *
from ndrangheta.entities import *
from networkx.drawing.nx_pydot import read_dot

class World:
    def __init__(self):
        self.towns = dict()
        self.families = dict()

    def add_town(self, t: Town):
        self.towns[t.id] = t

    def add_family(self, f: Family):
        self.families[f.id] = f

    def Family(self, f_id: FamilyID):
        return self.families[f_id]

    def Town(self, t_id: TownID):
        return self.towns[t_id]

    def towns_of_family(self, f_id: FamilyID):
        return [t for t in self.towns.values() if t.family.id == f_id]

    def print_cities(self, family_id, exclude_others=False):
        for tid, t in self.towns.items():
            if exclude_others and t.family.id != family_id:
                continue

            print(t.str_stats(t.family.id != family_id))

# =========================================================== #

def load_graph(fpath="ndrangheta/example.dot"):
    w = World()
    g = nx.Graph(read_dot(fpath))

    def convert_labels_to_int(g):
        new_g = nx.Graph()
        for n in g.nodes():
            if n.isnumeric(): #nodes representing cities
                new_g.add_node(int(n), **g.nodes()[n])
                new_g.add_edge(int(n), int(n))
            else: #metanodes
                new_g.add_node(n, **g.nodes()[n])
                
        for (x,y) in g.edges():
            new_g.add_edge(int(x), int(y))

        return new_g
    
    g = convert_labels_to_int(g)

    # =========================================================== #

    def sanitize_metanode(node: Dict) -> Dict:
        node["money"] = int(node.get("money", 1_000_000))
        node["family"] = int(node["family"])
        node["is_player"] = node.get("player", "f") == "t"
        if "player" in node:
            del node["player"]
        return node
    
    def extract_metanodes(g) -> Dict:
        out, to_remove = dict(), list()
        
        for n in g.nodes():
            if isinstance(n, str):
                d = sanitize_metanode(g.nodes()[n])
                out[d["family"]] = d
                to_remove.append(n)

        g.remove_nodes_from(to_remove)
        return out

    metainfo: Dict["FamilyID", Dict] = extract_metanodes(g)

    # =========================================================== #
    
    def map_nodes(f, g):
        for name in g.nodes():
            d = f(g.nodes()[name])
            nx.set_node_attributes(g, d)

    def sanitize_dot(node: Dict) -> Dict:
        node["family"] = int(node.get("family", 0))
        node["pop"]    = None if "pop" not in node else int(node["pop"]) * 1000
        node["hold"]   = None if "hold" not in node else float(node["hold"])
        node["drugs"]  = float(node.get("drugs", 0))
        node["capital"] = node.get("capital", "f") == "t"
        node["soldiers"] = int(node.get("soldiers", 0))
        node["leader"] = int(node.get("leader", 1))
        
        return node

    map_nodes(sanitize_dot, g)

    # =========================================================== #
    
    # TODO
    # if Family.FAMILIES != dict() or Town.TOWNS != dict():
    #     print("Polluted Family/Towns, resetting")
    #     Family.FAMILIES = dict()
    #     Town.TOWNS      = dict()
    
    # Crea istanze Town() / Family()
    for n in g.nodes():
        node      = g.nodes()[n]
        family_id = node["family"]

        # Famiglia non già aggiunta 
        if family_id not in w.families:
            if family_id not in metainfo:
                metainfo[family_id] = sanitize_metanode({"family": family_id})

            if family_id == -1:
                fam_obj = Police(-1, "Police",  metainfo[family_id], world=w)
            else:
                fam_obj = Family(family_id, str(family_id), metainfo[family_id], world=w)

            w.add_family(fam_obj)
                
        else:
            fam_obj = w.Family(family_id)

            
        t = Town(n, fam_obj, world=w,
                 hold=node["hold"], pop=node["pop"], drugs=node["drugs"],
                 soldiers=node["soldiers"], leader=node["leader"], capital=node["capital"])
        
        if node["capital"]:
            fam_obj.capital = n

        w.add_town(t)
        
    # Sanity checks:
    for f in w.families.values():
        if f.capital is None:
            raise Exception(f"Family {f.id} has no capital!")
        
    return (w, g)
