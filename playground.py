def f(a, *args, __act=5, **kwargs):
    print(a, args, __act, kwargs)

f(1, 2, act="action", banana=34)