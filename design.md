## External interface
How does the world at large (or non-microservice internal stuff) communicate to this framework?

TBD

The problem:
-  Requests to an MS must take a very particular format.
-  The response to a request might come from a different MS instance than received the original request


On k8s:
-  Each MS can be exposed with an external IP address, if desired.

Ideas:
- For code interactions: Expose API and expect users to pack/unpack requests correctly
    - Swagger might provide this easily.
- For webservice exposure: "normal" python webserver that translates from normal HTTP requests to MS requests
    - Stateful webserver terminates external HTTP requests.
    - Basically implements "Ask" from the actor model
        - Sends requests to MS's as desired.
        - Waits for the corresponding result
        - Sends response to the HTTP request

## Actors
- Flask
    - Fronted by Gunicorn
        - Running Sync workers by default (apparently best for CPU or network bound)
        - Optionally running asyncio works (gthread or gaiohttp?) if requested
            - For MS's that use IO - access to disk or non-MS network requests
        - Probably default to 1 worker with a 2 threads?
            - Allow user to tune these options for each MS.


## Communication
Basis: Actor model
Each microservice is an actor.
Each call to another MS is made asynchronously.
Responses are simply requests re-run the entire function but, to avoid the infinite loop,
the request that contains the response contains the response for the service call. This framework detects
that the service has already been called, and doesn't call it again.
If multiple service calls are made in a function, the results from each called service are
aggregated in the calls.
This means we're passing information around that isn't strictly necessary, but
the benefit is that it makes the individual services stateless.

Consider this function:

```
@microservice
def my_func(*args, **kwargs):
    res1 = my_service(*args, **kwargs)
    res2 = my_service2(*args, **kwargs)
    return res1 + res2
```

where `my_service` and `my_service2` are microservices.

Suppose that `my_func` is called by `original_caller`

The call to `my_service` contains data like the following:

```
{
	'_args': *args,
	'_kwargs': **kwargs,
	'_via': [
	    'original_caller',
	    'microservice.my_func',
    ],
	'_results': {},
}
```

The response from `my_service` calling into `my_func` contains the data:

```
{
	'_args': *args,
	'_kwargs': **kwargs,
	'_via': [
	    'original_caller',
    ],
	'_results': {
        'microservice.my_func': {'microservice.my_service': (*response_values)},
	},
}
```

The `_results` contain the name of the service which the result is relevant for.
This allows calls to the same service from multiple different services in the evaluation chain.

The wrapper to call `my_service` notices that the result already exists, so just returns that.
Then the request to `my_service2` is made:

```
{
	'_args': *args,
	'_kwargs': **kwargs,
	'_via': [
	    'original_caller',
	    'microservice.my_func',
    ],
	'_results': {
        'microservice.my_func': {'microservice.my_service': (*response_values)},
	},
}
```

And the response is:

```
{
	'_args': *args,
	'_kwargs': **kwargs,
	'_via': [
	    'original_caller',
    ],
	'_results': {
        'microservice.my_func': {'microservice.my_service': (*response_values)},
        'microservice.my_func': {'microservice.my_service2': (*response_values2)},
	},
}
```

And finally, the response from `my_func` to `original_caller` is sent.


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
