import collections
db = collections.defaultdict(dict)


def f(a, b, *args, ab=1, bc=2, **kwargs):
    print(a, b, args, ab, bc, kwargs)

f(1, 2, 3, 4, 5, ab=2, bc=5, asdf=234)
f(1, 2, 3, 4, 5, bc=5, asdf=234)
f(bc=5, ab=34, *(1, 2, 3, 4, 5), asdf=234)

exit()

import requests
req = requests.get(
    "http://192.168.99.100:5000/microservice.examples.hello_world.hello_world",
    json={
        '_args': tuple(),
        '_kwargs': {},
    }
)
print(req)
print(req.text)

exit()


class Test:
    __as = 234
    _as = 345
    a = "aa"
    b = "bb"

    def __init__(self):
        self._my_prop = "my_prop_base"

    def func(self):
        return 234

    def func2(self):
        return self.a

    @property
    def my_prop(self):
        return self._my_prop

    @my_prop.setter
    def my_prop(self, value):
        self._my_prop = value

    def __getattribute__(self, item):
        print("getting_base %s" % item)
        orig = super(Test, self).__getattribute__(item)
        return orig


class Override(Test):
    __uri = "uri1"

    def __init__(self, *args, **kwargs):
        print("here")
        print(dir(self))
        print(self.__asd)
        for attr in [at for at in dir(self) if '__' not in at]:
            value = getattr(super(Override, self), attr)
            print(attr, value)
            db[self.__uri][attr] = value
        super(Override, self).__init__(*args, **kwargs)

    def __getattribute__(self, item):
        if item.startswith('_Override__'):
            return
        orig = super(Override, self).__getattribute__(item)
        if callable(orig):
            return orig
        print("getting %s" % item)
        return db[self.__uri].get(item, "non existent")

    def __setattr__(self, key, value):
        super(Override, self).__setattr__(key, value)
        print("setting %s: %s" % (key, value))
        if key.startswith('__'):
            return
        # Get the value after setting it so that any properties in the super class get run first.
        db[self.__uri][key] = getattr(super(Override, self), key)

# t = Test()
#
# print(t)
# print(t.a)
# print(t.b)
# print(t.func)
# print(t.func())
# print(t._my_prop)
# print(t._as)
# print(t.__as)
# exit()

t = Override()

print(t)
print(t.a)
print(t.b)
print(t.func)
print(t.func())
print(t.func2())
print(t._my_prop)
print(t.__as)
