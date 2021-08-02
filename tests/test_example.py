import unittest
import random

from ndrangheta.graph import *

class BasicsTestCase(unittest.TestCase):
    
    def test_example(self):
        g = load_graph("tests/dots/simple")
        env = Environment(g)

        self.assertEqual(
            env.safest_path(7, 4),
            [7,3,4]
        )
        
        self.assertEqual(
            env.safest_path(7, 5),
            [7,3,4,6,5]
        )

        self.assertEqual(
            env.safest_path(0, 3),
            [0, 2, 4, 3]
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
