## Musings
Should be as easy to make a function into a MS by doing:

    @microservice
    def my_func(arg_1, arg_2):
        pass

That requires:
  - A microservice discovery centre
  - An orchestrator to spin up microservices
    - This also needs to be able to monitor usage of individual microservices and scale sideways
    - That means load balancers
      - How to deal with maxing out the LB? If this has happened, then the MS that is driving the LB should itself be scaled sideways.
  - A generic load balancer


So old code that looked like:

    def my_func(x):
        p1 = a(x)
        p2 = b(p2)
        p3 = c(p3)
        return p3

    def a(x):
        sleep(1)
        return x

    def b(x):
        sleep(2)
        return x

    def c(x):
        sleep(3)
        return x
Now looks like:

    from A import a
    from B import b
    from C import c


    def my_func(x):
        p1 = a(x)
        p2 = b(p2)
        p3 = c(p3)
        return p3

    # These are actually now all in different packages
    @microservice
    def a(x):
        sleep(1)
        return x

    @microservice
    def b(x):
        sleep(2)
        return x

    @microservice
    def c(x):
        sleep(3)
        return x

Where `microservice` looks a bit like

    def microservice(function):
        """
        Decorator that replaces the function with the restful call to make.
        """
        micro_function = discover(function)
        return micro_function

    def discover(function):
        uri = orchestration.access(function)
        def ms_function(*args, **kwargs):
            restful_function = make_restful(uri, *args, **kwargs)
        return ms_function

    def make_restful(uri, *args, **kwargs):
        # uses requests...
        return <function to call>

    class Orchestrator:
        # An instance of a MS *is* a resource, so refer to it as a uri.
        services = {'service_name': [uris]}
        # Is actually itself a MS
