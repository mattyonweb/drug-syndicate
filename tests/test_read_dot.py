import unittest
from typing import *

from ndrangheta.read_dot import load_graph
from ndrangheta.entities import *

class TestSafePathGraph(unittest.TestCase):
    def test_all_attributes_exist(self):
        g = load_graph("tests/dots/simple.dot")

        self.assertTrue(all("pop" in g.nodes()[n] for n in g.nodes()))
        self.assertTrue(all("family" in g.nodes()[n] for n in g.nodes()))
        self.assertTrue(all("hold" in g.nodes()[n] for n in g.nodes()))

    def test_defined_population_and_hold(self):
        g = load_graph("tests/dots/inevitable_family.dot")

        self.assertEqual(Town.get(7).population, 99000)
        self.assertEqual(Town.get(7).hold, 0.7)

        
