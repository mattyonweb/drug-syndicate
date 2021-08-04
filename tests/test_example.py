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

# =========================================================== #

    def test_shipments(self):
        random.seed(100)
        g = load_graph("tests/dots/inevitable_family.dot")
        env = Environment(g)
        narcos = Narcos()

        
        try:
            s = Shipment(kgs=5, costed=10_000, destination=1)        
            env.send_shipment_safest(0, 1, s)
            self.fail("No drug!")
        except ShipmentError:
            pass

        
        family = Family.get(0)
        family.money = 0
        try:
            narcos.sell_drugs(3, family, dest=0)
            self.fail("Shouldnt have enough money!")
        except DrugError:
            pass
        
        family.money = 1_000_000
        narcos.sell_drugs(3, family, dest=0)
        
        try:
            env.send_shipment_safest(0, 1, s)
            self.fail("You shouldnt have enough drug!")
        except ShipmentError:
            pass

        s = Shipment(kgs=2.5, costed=10_000, destination=1)
        env.send_shipment_safest(0, 1, s)
        self.assertGreater(Town.get(1).drugs, 0)
        self.assertAlmostEqual(Town.get(0).drugs, 0.5)

        s = Shipment(kgs=0.5, costed=10_000, destination=1)
        env.send_shipment_safest(0, 1, s)
        self.assertAlmostEqual(Town.get(0).drugs, 0)

        try:
            s = Shipment(kgs=1, costed=10_000, destination=1)
            env.send_shipment_safest(0, 1, s)
            self.fail("Shouldnt have enough drug to send!")
        except ShipmentError:
            pass
        
def asd(lol):
    return lol
