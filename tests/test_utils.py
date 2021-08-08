import unittest
from unittest.mock import *
import random

from ndrangheta.utils import *
from ndrangheta.entities import *
from ndrangheta.graph import *

class TestRequestsFromLocalFamilies(unittest.TestCase):
    def test_montecarlo(self):
        for _ in range(100):
            if montecarlo(1.0):
                self.fail("")

        for _ in range(100):
            if not montecarlo(0.0):
                self.fail("")

        t, f = 0,0
        for _ in range(10_00000):
            if montecarlo(0.5):
                t+=1
            else:
                f+=1

        self.assertAlmostEqual(t, f, delta=2000)


    def random_ship(self, fam):
        return Shipment(random.randint(1, 10), random.randint(1000, 4000), fam)

    
    def test_loss_shipment(self):
        g = load_graph("tests/dots/forced-path-low.dot")
        s = Simulator(g)

        # Passaggio su città amica e leale
        for _ in range(100):
            ship = self.random_ship(0)

            self.assertAlmostEqual(
                Town.get(0).transit_shipment(ship),
                1,
                delta=0.01
            )

        # passaggio su città nemica ma poco leale
        for _ in range(100):
            ship = self.random_ship(0)

            self.assertAlmostEqual(
                Town.get(1).transit_shipment(ship),
                1,
                delta=0.01
            )

        # passaggio su città nemica molto leale
        for _ in range(100):
            ship = self.random_ship(1)

            self.assertAlmostEqual(
                Town.get(0).transit_shipment(ship),
                0,
                delta=0.01
            )

        # In media città (amiche) con hold alto mantengono più droga ad ogni passaggio
        mult_3, mult_4 = 0, 0
        for _ in range(100):
            ship = self.random_ship(0)

            mult_3 += Town.get(3).transit_shipment(ship)
            mult_4 += Town.get(4).transit_shipment(ship) #hold 4 > hold 3, entrambea miche

        self.assertGreater(mult_4, mult_3)

        
        # Città ostili con hold maggiore tendono a rubare più spesso il package
        mult_3, mult_4 = 0, 0
        for _ in range(1000):
            ship = self.random_ship(1)

            mult_3 += Town.get(3).transit_shipment(ship)
            mult_4 += Town.get(4).transit_shipment(ship) #hold 4 > hold 3, entrambea miche

        self.assertGreater(mult_3, mult_4)
        self.assertAlmostEqual(mult_4, 1000/2, delta=40)
        
