import unittest
from typing import *

from ndrangheta.read_dot import load_graph
from ndrangheta.entities import *

class TestSafePathGraph(unittest.TestCase):
    def setUp(self):
        self.w, self.g = load_graph("tests/dots/graph_with_all_attributes.dot")

    def test_all_attributes_exist(self):
        self.assertTrue(all("pop" in self.g.nodes()[n] for n in self.g.nodes()))
        self.assertTrue(all("family" in self.g.nodes()[n] for n in self.g.nodes()))
        self.assertTrue(all("hold" in self.g.nodes()[n] for n in self.g.nodes()))
        self.assertTrue(all("drugs" in self.g.nodes()[n] for n in self.g.nodes()))

        
    def test_defined_population_and_hold(self):
        self.assertEqual(self.w.town(0).family.id, 1)
        self.assertEqual(self.w.town(1).family.id, 0)
        self.assertEqual(self.w.town(2).family.id, 3)
        self.assertEqual(self.w.town(3).family.id, 2)
        
        self.assertAlmostEqual(self.w.town(3).hold, 0.6)
        
        self.assertEqual(self.w.town(0).population, 50000)
        self.assertEqual(self.w.town(1).population, 99000)
        
        self.assertEqual(self.w.town(1).drugs, 100)
        self.assertEqual(self.w.town(0).drugs, 0)
        self.assertEqual(self.w.town(2).drugs, 0)
        self.assertEqual(self.w.town(3).drugs, 0)

        
    def test_metanodes(self):
        self.assertEqual(self.w.family(0).money, 1_000_000)
        self.assertEqual(self.w.family(1).money, 0)
        self.assertEqual(self.w.family(2).money, 1_000_000)
        self.assertEqual(self.w.family(3).money, 200_000)

        
    def test_war_attributes(self):
        self.w, self.g = load_graph("tests/dots/war-scenario-1.dot")

        self.assertEqual(self.w.town(0).local_family.soldiers, 50)
        self.assertEqual(self.w.town(1).local_family.soldiers, 40)
        
        self.assertEqual(self.w.town(0).local_family.leader, 1)
        self.assertEqual(self.w.town(1).local_family.leader, 2)

        

        
