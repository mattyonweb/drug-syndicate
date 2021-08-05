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
        
    
class TestNextStep(unittest.TestCase):
    def setUp(self):
        self.s = Simulator(load_graph("tests/dots/simple.dot"))
        
    def test_advance_time_no_exception_when_no_drugs_whatsoever(self):
        self.s.advance_time()

    
