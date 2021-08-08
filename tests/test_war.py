import unittest
import random

from ndrangheta.graph import *
from ndrangheta.entities import *
from ndrangheta.read_dot import load_graph

class TestRequestsFromLocalFamilies(unittest.TestCase):
    def setUp(self):
        self.s = Simulator(load_graph("tests/dots/war-scenario-1.dot"))
        self.family = Family.get(id=0)

    def test_cant_declare_war_if_high_hold(self):
        try:
            self.s.declare_war(0, 1)
            self.fail("shoulnd possible declare war hold is too high!")
        except WarError:
            pass

    def test_change_ownership_after_succesfull_fight(self):
        self.s.declare_war(0, 4)
        self.assertEqual(Town.get(4).family, 0)

    
    def test_change_ownership_after_succesfull_fight(self):
        self.s.declare_war(0, 4)
        self.assertEqual(Town.get(4).family, 0)
