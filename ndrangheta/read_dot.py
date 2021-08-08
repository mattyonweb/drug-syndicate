from typing import *
import networkx as nx
import matplotlib.pyplot as plt

from ndrangheta.config import *
from ndrangheta.entities import *
from networkx.drawing.nx_pydot import read_dot

def load_graph(fpath="ndrangheta/example.dot"):
    g = nx.Graph(read_dot(fpath))

    def convert_labels_to_int(g):
        new_g = nx.Graph()
        for n in g.nodes():
            new_g.add_node(int(n), **g.nodes()[n])
            new_g.add_edge(int(n), int(n))
        for (x,y) in g.edges():
            new_g.add_edge(int(x), int(y))

        return new_g
    
    g = convert_labels_to_int(g)

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

    # TODO
    if Family.FAMILIES != dict() or Town.TOWNS != dict():
        print("Polluted Family/Towns, resetting")
        Family.FAMILIES = dict()
        Town.TOWNS      = dict()

        
    # Crea istanze Town() / Family()
    for n in g.nodes():
        node = g.nodes()[n]
        
        family = node["family"] 
        if family not in Family.FAMILIES:
            if family == -1:
                Police(-1, "Police")
            else:
                Family(family, str(family))

        t = Town(n, family,
                 hold=node["hold"], pop=node["pop"], drugs=node["drugs"],
                 soldiers=node["soldiers"], leader=node["leader"], capital=node["capital"])
        
        if node["capital"]:
            Family.get(family).capital = n
            
    # Sanity checks:
    for f in Family.FAMILIES.values():
        if f.capital is None:
            raise Exception(f"Family {f.id} has no capital!")
        
    return g
