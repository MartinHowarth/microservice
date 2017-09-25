import json

from unittest import TestCase

from microservice.core.load_balancer import LocalLoadBalancer


class TestLocalLoadBalancer(TestCase):
    def test_next(self):
        llb = LocalLoadBalancer([1, 2, 3])
        self.assertEqual(next(llb), 1)
        self.assertEqual(next(llb), 2)
        self.assertEqual(next(llb), 3)
        self.assertEqual(next(llb), 1)

    def test_append(self):
        llb = LocalLoadBalancer([1, 2, 3])
        self.assertEqual(next(llb), 1)
        self.assertEqual(next(llb), 2)
        self.assertEqual(next(llb), 3)
        self.assertEqual(next(llb), 1)

        llb.append(4)
        self.assertEqual(next(llb), 1)
        self.assertEqual(next(llb), 2)
        self.assertEqual(next(llb), 3)
        self.assertEqual(next(llb), 4)
        self.assertEqual(next(llb), 1)

    def test_extend(self):
        llb = LocalLoadBalancer([1, 2, 3])
        self.assertEqual(next(llb), 1)
        self.assertEqual(next(llb), 2)
        self.assertEqual(next(llb), 3)
        self.assertEqual(next(llb), 1)

        llb.extend([4, 5, 6])
        self.assertEqual(next(llb), 1)
        self.assertEqual(next(llb), 2)
        self.assertEqual(next(llb), 3)
        self.assertEqual(next(llb), 4)
        self.assertEqual(next(llb), 5)
        self.assertEqual(next(llb), 6)
        self.assertEqual(next(llb), 1)

    def test_jsonify(self):
        llb = LocalLoadBalancer([1, 2, 3])
        js = json.dumps(llb)
        self.assertEqual(js, '[1, 2, 3]')
