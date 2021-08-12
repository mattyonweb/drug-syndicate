import unittest
import random

from ndrangheta.graph import *
from ndrangheta.read_dot import load_graph

class TestSafePathGraph(unittest.TestCase):
    def test_base(self):
        w,g = load_graph("tests/dots/simple.dot")
        r = Routing(w,g)

        
        self.assertEqual(
            r.automatic_path(7, 4, r.safest_path_heuristic),
            [7,5,3,6,4]
        )
        
        self.assertEqual(
            r.automatic_path(7, 3, r.safest_path_heuristic),
            [7,5,3]
        )

        self.assertEqual(
            r.automatic_path(0, 1, r.safest_path_heuristic),
            [0, 1]
        )
                
        try:
            r.automatic_path(0, 7, r.safest_path_heuristic)
            self.fail("Different families!")
        except ShipmentError:
            pass

        r.automatic_path(0, 0, r.safest_path_heuristic)

        
    def test_circle(self):
        w,g = load_graph("tests/dots/low_trust_path.dot")
        r = Routing(w,g)

        self.assertEqual(
            r.automatic_path(0, 6, r.safest_path_heuristic),
            [0,1,2,3,4,5,6]
        )

    def test_inevitable_enemy_family(self):
        w,g = load_graph("tests/dots/inevitable_family.dot")
        r = Routing(w,g)

        self.assertEqual(
            r.automatic_path(0, 6, r.safest_path_heuristic),
            [0,7,6]
        )

# =========================================================== #

class TestSafeShipmentGraph(unittest.TestCase):
    def setUp(self):
        self.w, self.g = load_graph("tests/dots/inevitable_family.dot")
        self.r = Routing(self.w,self.g)
        self.narcos = Narcos(self.w)
        self.family = self.w.Family(0)
        
    def test_01_cant_send_drugs_if_no_drug_in_city(self):       
        s = Shipment(kgs=5, retail_price_kg=10_000, author=0)   

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
        s = Shipment(kgs=5, retail_price_kg=10_000, author=0)
        
        self.family.money = 1_000_000
        self.narcos.sell_drugs(3, self.family, dest=0)
        
        try:
            self.r.send_shipment_safest(0, 1, s)
            self.fail("You shouldnt have enough drug!")
        except ShipmentError:
            pass

    def test_04_everything_correct_should_send_drug(self):
        self.family.money = 1_000_000
        self.narcos.sell_drugs_immediately(3, self.family, dest=0)
        
        s = Shipment(kgs=2.5, retail_price_kg=10_000, author=0)
        self.r.send_shipment_safest(0, 1, s)
        self.assertGreater(self.w.Town(1).drugs, 0)
        self.assertAlmostEqual(self.w.Town(0).drugs, 0.5)

        # Sends a second tranche of remmaining drugs
        s = Shipment(kgs=0.5, retail_price_kg=10_000, author=0)
        self.r.send_shipment_safest(0, 1, s)
        self.assertAlmostEqual(self.w.Town(0).drugs, 0)

    def test_05_cant_send_drugs_to_enemy_family(self):
        try:
            self.narcos.sell_drugs(1, self.family, 7)
            self.fail("Shouldnt buy drug for other families!")
        except ShipmentError:
            pass
        
