import unittest
import random

from ndrangheta.graph import *

class TestGraph(unittest.TestCase):
    def test_base(self):
        g = load_graph("tests/dots/simple.dot")
        env = Environment(g)
        
        self.assertEqual(
            env.safest_path(7, 4),
            [7,5,3,6,4]
        )
        
        self.assertEqual(
            env.safest_path(7, 3),
            [7,5,3]
        )

        self.assertEqual(
            env.safest_path(0, 1),
            [0, 1]
        )
                
        try:
            env.safest_path(0, 7)
            self.fail("Different families!")
        except ShipmentError:
            pass

        try:
            env.safest_path(0, 0)
            self.fail("Origin = destination!")
        except ShipmentError:
            pass

    def test_circle(self):
        g = load_graph("tests/dots/low_trust_path.dot")
        env = Environment(g)

        self.assertEqual(
            env.safest_path(0, 6),
            [0,1,2,3,4,5,6]
        )

    def test_inevitable_enemy_family(self):
        g = load_graph("tests/dots/inevitable_family.dot")
        env = Environment(g)

        self.assertEqual(
            env.safest_path(0, 6),
            [0,7,6]
        )
