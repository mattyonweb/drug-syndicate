import unittest
import random

from ndrangheta.graph import *
from ndrangheta.read_dot import load_graph

class TestSafePathGraph(unittest.TestCase):
    def test_base(self):
        g = load_graph("tests/dots/simple.dot")
        r = Routing(g)

        
        self.assertEqual(
            r.safest_path(7, 4),
            [7,5,3,6,4]
        )
        
        self.assertEqual(
            r.safest_path(7, 3),
            [7,5,3]
        )

        self.assertEqual(
            r.safest_path(0, 1),
            [0, 1]
        )
                
        try:
            r.safest_path(0, 7)
            self.fail("Different families!")
        except ShipmentError:
            pass

        try:
            r.safest_path(0, 0)
            self.fail("Origin = destination!")
        except ShipmentError:
            pass

    def test_circle(self):
        g = load_graph("tests/dots/low_trust_path.dot")
        r = Routing(g)

        self.assertEqual(
            r.safest_path(0, 6),
            [0,1,2,3,4,5,6]
        )

    def test_inevitable_enemy_family(self):
        g = load_graph("tests/dots/inevitable_family.dot")
        r = Routing(g)

        self.assertEqual(
            r.safest_path(0, 6),
            [0,7,6]
        )

# =========================================================== #

class TestSafeShipmentGraph(unittest.TestCase):
    def setUp(self):
        self.r = Routing(load_graph("tests/dots/inevitable_family.dot"))
        self.narcos = Narcos()
        self.family = Family.get(0)
        
    def test_01_cant_send_drugs_if_no_drug_in_city(self):       
        s = Shipment(kgs=5, costed=10_000, destination=1)   

        try:
            self.r.send_shipment_safest(0, 1, s)
            self.fail("No drug!")
        except ShipmentError:
            pass

    def test_02_cant_buy_from_narcos_if_not_enough_money(self):
        self.family.money = 0
        try:
            self.narcos.sell_drugs(3, self.family, dest=0)
            self.fail("Shouldnt have enough money!")
        except DrugError:
            pass

    def test_03_cant_send_more_drug_than_owned(self):
        s = Shipment(kgs=5, costed=10_000, destination=1)
        
        self.family.money = 1_000_000
        self.narcos.sell_drugs(3, self.family, dest=0)
        
        try:
            self.r.send_shipment_safest(0, 1, s)
            self.fail("You shouldnt have enough drug!")
        except ShipmentError:
            pass

    def test_04_everything_correct_should_send_drug(self):
        self.family.money = 1_000_000
        self.narcos.sell_drugs(3, self.family, dest=0)
        
        s = Shipment(kgs=2.5, costed=10_000, destination=1)
        self.r.send_shipment_safest(0, 1, s)
        self.assertGreater(Town.get(1).drugs, 0)
        self.assertAlmostEqual(Town.get(0).drugs, 0.5)

        # Sends a second tranche of remmaining drugs
        s = Shipment(kgs=0.5, costed=10_000, destination=1)
        self.r.send_shipment_safest(0, 1, s)
        self.assertAlmostEqual(Town.get(0).drugs, 0)
        
def asd(lol):
    return lol
