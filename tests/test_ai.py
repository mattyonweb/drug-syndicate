from typing import *
import unittest
import random

from ndrangheta.graph import *
from ndrangheta.read_dot import load_graph

class TestSafePathGraph(unittest.TestCase):
    def test_base(self):
        g = load_graph("tests/dots/simple.dot")
        self.sim = Simulator(g)

        proposals_0 = Town.get(2).ai_proposals(),

        for city_id in range(4):
            reqs = Town.get(city_id).ai_proposals()
            
            self.assertIsInstance(reqs, list)
            if len(reqs) > 0:
                self.assertIsInstance(reqs[0], Request)
            
        self.assertTrue(
            self.sim.ai.sort_ai_cities_proposals(family_id=0)[0],
            proposals_0
        )

        

        
        
