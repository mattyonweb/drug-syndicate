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
            self.s.declare_war(0, 0, 1)
            self.fail("shoulnd possible declare war hold is too high!")
        except WarError:
            pass

    def test_change_ownership_after_succesfull_fight(self):
        self.s.declare_war(0, 0, 4)
        self.assertEqual(Town.get(4).family.id, 0)
        self.assertEqual(Town.get(4).local_family.parent.id, 0)

        self.s.declare_war(0, 0, 6)
        self.assertEqual(Town.get(6).family.id, 1)

    
    def test_leader_variation_after_war(self):
        lvl_0 = Town.get(0).local_family.leader
        
        self.s.declare_war(0, 0, 4)
        self.assertEqual(Town.get(0).local_family.leader, lvl_0 + 0.5)
        self.assertEqual(Town.get(4).local_family.leader, 1)

        lvl_0 = Town.get(0).local_family.leader
        lvl_6 = Town.get(6).local_family.leader
        self.s.declare_war(0, 0, 6)
        self.assertEqual(Town.get(0).local_family.leader, lvl_0 - 1)
        self.assertEqual(Town.get(6).local_family.leader, lvl_6 + 1)

        
    def test_hold_variation_after_war(self):
        h0 = Town.get(0).hold
        h4 = Town.get(4).hold
        
        self.s.declare_war(0, 0, 4)
        self.assertEqual(Town.get(0).hold, h0+0.08)
        self.assertEqual(Town.get(4).hold, 0.7)

        h0 = Town.get(0).hold
        h6 = Town.get(6).hold
        self.s.declare_war(0, 0, 6)
        self.assertEqual(Town.get(0).hold, h0-0.08)
        self.assertEqual(Town.get(6).hold, 0.7)

        
    def test_soldiers_variation(self):
        pass #?

    def test_conquer_capital(self):
        from collections import Counter
        self.s.declare_war(0, 0, 7)
        
        c = Counter([t.family for t in Town.TOWNS.values()])
        self.assertTrue(
            len([x for x in c if c[x] >= 2]) == 1
        )
        self.assertTrue(
            all(x > 0 for x in c.values())
        )
