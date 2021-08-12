import unittest
import random

from ndrangheta.graph import *
from ndrangheta.entities import *
from ndrangheta.read_dot import load_graph

class TestRequestsFromLocalFamilies(unittest.TestCase):
    def setUp(self):
        self.s = Simulator(load_graph("tests/dots/two_nodes.dot"))
        self.family = Family.get(id=0)
        
    def test_basic_ai(self):
        self.s.advance_time()

        self.s.ai.decide_shipments(self.family.id)

        self.s.advance_time()

        # self.assertEqual(len(Family.get(0).drug_requests), 0)
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

        
    def test_local_families_pay_weekly_taxes(self):
        town = Town.get(0)
        
        town.local_family.money = 1_000_000
        town.population = 1

        money = Family.get(0).money

        #####
        
        Family.get(0).change_tax_in(town_id=0, new_tax_rate=0.20)

        self.s.advance_time(turns=8)

        self.assertAlmostEqual(town.local_family.money, 800_000, delta=5_000)
        self.assertAlmostEqual(Family.get(0).money, money + 200_000, delta=5_000)

        #####
        
        Family.get(0).change_tax_in(town_id=0, new_tax_rate=1.0)
        
        self.s.advance_time(turns=8)
        self.assertAlmostEqual(town.local_family.money, 0, delta=1)
        self.assertAlmostEqual(Family.get(0).money, money + 1_000_000, delta=5_000)


    def test_call_off_request_if_somehow_local_family_get_hold_of_drugs(self):
        town = Town.get(0)
        town.money = 0
        town.drugs = 0

        self.s.advance_time()

        # self.assertTrue(any(r.author == 0 for r in Family.get(0).drug_requests))

        self.s.buy_from_narcos(family_id=0, kgs=10, immediate=True)
        self.assertEqual(town.drugs, 10)
        
        self.s.advance_time()

        # town ha ritirato la richiesta
        # self.assertFalse(
        #     any(r.author == 0 for r in Family.get(0).drug_requests)
        # )
        
        
class TestNextStep(unittest.TestCase):
    def setUp(self):
        self.s = Simulator(load_graph("tests/dots/simple.dot"))
        
    def test_advance_time_no_exception_when_no_drugs_whatsoever(self):
        self.s.advance_time()

    
