import itertools


# TODO this would work better with a class decorator or a MetaClass to call `self.cycle = itertools.cycle(self)`
# after each function.
# Could also be updated to keep it's place when the cycle is reset - otherwise things at the start of the list are
# used more often if additional elements are added.
class LocalLoadBalancer(list):
    cycle = None

    def __init__(self, *args, **kwargs):
        super(LocalLoadBalancer, self).__init__(*args, **kwargs)
        self.cycle = itertools.cycle(self)

    def append(self, *args, **kwargs):
        super(LocalLoadBalancer, self).append(*args, **kwargs)
        self.cycle = itertools.cycle(self)

    def extend(self, *args, **kwargs):
        super(LocalLoadBalancer, self).extend(*args, **kwargs)
        self.cycle = itertools.cycle(self)

    def insert(self, *args, **kwargs):
        super(LocalLoadBalancer, self).insert(*args, **kwargs)
        self.cycle = itertools.cycle(self)

    def remove(self, *args, **kwargs):
        super(LocalLoadBalancer, self).remove(*args, **kwargs)
        self.cycle = itertools.cycle(self)

    def pop(self, *args, **kwargs):
        super(LocalLoadBalancer, self).pop(*args, **kwargs)
        self.cycle = itertools.cycle(self)

    def __next__(self):
        return next(self.cycle)
