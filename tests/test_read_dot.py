import unittest
from typing import *

from ndrangheta.read_dot import load_graph
from ndrangheta.entities import *

class TestSafePathGraph(unittest.TestCase):
    def setUp(self):
        self.g = load_graph("tests/dots/graph_with_all_attributes.dot")

    def test_all_attributes_exist(self):
        self.assertTrue(all("pop" in self.g.nodes()[n] for n in self.g.nodes()))
        self.assertTrue(all("family" in self.g.nodes()[n] for n in self.g.nodes()))
        self.assertTrue(all("hold" in self.g.nodes()[n] for n in self.g.nodes()))
        self.assertTrue(all("drugs" in self.g.nodes()[n] for n in self.g.nodes()))

    def test_defined_population_and_hold(self):
        g = load_graph("tests/dots/graph_with_all_attributes.dot")

        
        self.assertEqual(Town.get(0).family, 1)
        self.assertEqual(Town.get(1).family, 0)
        self.assertEqual(Town.get(2).family, 3)
        self.assertEqual(Town.get(3).family, 2)
        
        self.assertAlmostEqual(Town.get(3).hold, 0.6)
        
        self.assertEqual(Town.get(0).population, 50000)
        self.assertEqual(Town.get(1).population, 99000)
        
        self.assertEqual(Town.get(1).drugs, 100)
        self.assertEqual(Town.get(0).drugs, 0)
        self.assertEqual(Town.get(2).drugs, 0)
        self.assertEqual(Town.get(3).drugs, 0)

        
