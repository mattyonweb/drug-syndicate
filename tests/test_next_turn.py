import unittest
import random

from ndrangheta.graph import *
from ndrangheta.entities import *
from ndrangheta.read_dot import load_graph

class TestRequestsFromLocalFamilies(unittest.TestCase):
    def setUp(self):
        self.s = Simulator(load_graph("tests/dots/two_nodes.dot"))
        self.family = Family.get(id=0)

    def test_citiyes_do_request_quest_mark(self):
        self.s.advance_time()
        
        self.assertEqual(
            len(self.family.drug_requests), 1,
            "\n".join(str(r) for r in self.family.drug_requests)
        )
        
    def test_basic_ai(self):
        self.s.advance_time()

        self.s.ai.decide_shipments(self.family.id)

        self.s.advance_time()

        self.assertEqual(len(Family.get(0).drug_requests), 0)
        self.assertGreater(Town.get(1).drugs, 0)

    def test_when_stolen_package_city_increase_its_drugs(self):
        self.s = Simulator(load_graph("tests/dots/truly_inevitable_family.dot"))
        
        self.s.send_shipment(0, 6, Shipment(100, -1, 6))
        self.s.advance_time()

        Town.print_cities(1)
        
        self.assertGreater(Town.get(7).drugs, 100)

    def test_when_a_day_passes_local_families_get_richer_bc_of_drug_sold(self):
        old_money = Town.get(0).local_family.money
        self.s.advance_time()
        self.assertGreater(Town.get(0).local_family.money, old_money)

    def test_update_drug_retail_price_when_received_new_package(self):
        ship = Shipment(2, 90_000, 0)
        self.s.send_shipment(0, 1, ship)
        self.s.advance_time()
        self.assertEqual(ship.price_per_kg, Town.get(1).local_family.drug_cost_per_kg)
        
    
class TestNextStep(unittest.TestCase):
    def setUp(self):
        self.s = Simulator(load_graph("tests/dots/simple.dot"))
        
    def test_advance_time_no_exception_when_no_drugs_whatsoever(self):
        self.s.advance_time()

    
