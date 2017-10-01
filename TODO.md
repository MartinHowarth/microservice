# TODO

A set of pretty basic requirements that need implementing.
Generally aim to implement *something* with the expectation that it could be ripped out easily.
Learn and improve!

- Automatic test suite
- Additional testing:
    - More complicated import models
    - Interaction with other decorators
- Improve healthchecking:
    - all MS should publish their status every N seconds.
    - orchestrators subscribe to heartbeat notifications
    - when MS dies, it updates it's heartbeat about that too.
    - Deal with the case where a service is too congested to send a heartbeat in a timely manner
        - probably want to put non-responsive MS's in a quarantine for N time until they either start responding, or we declare them dead
- Split out the consumer/provider subscriptions from the orchestrator so that we can support e.g. crossbar to provide that service later
    - I think it works as follows:
        - MS_A -> O "Can has MS_B please"
        - O -> MS_A "here is all the MS_B's"
        - MS_A <stores those MS_B's>
        - MS_A <spins off thread to do:
            - MS_A -> S "I would like updates about MS_B please"
            >
        - MS_A -> MS_B "do work please" (as normal)
        And then the standard "pub" part of the subpub:
        ...
        - MS_B1 dies
        - O healthchecks "he's ded doc"
        - O -> S "yo dawg, MS_B1 ded"
        - S -> MS_A "RIP: MS_B1"
        ...
        - MS_B2 created
        - O -> S "sup, we got a new friend called MS_B2, he does MS_B for a living"
        - S -> MS_A "please start sending work to MS_B2 as well"
        ...
        - MS_A dies
        - S notices somehow? Or is told by O

- Add (more) robustness to the MS requests - deal with requests failing, and retry (expecting that the health checker will have recovered it)
    - Deal with orchestrator falling over
    - Deal with death of MS during startup (I think specifically losing connection during connection setup, rather than the connection just being refused)
- Support multiple orchestrators
    - Need to healthcheck and respawn each other
    - Need to share service knowledge (both creation and deletion)
        - When notified about a service by another orchestrator, add it to quarantine until you can healthcheck it.
- Add object support
    - Currently this only works for functions
    - Can we make it work for objects too?
    - Needs:
        - DB service
            - Ship a sample DB and a sample wrapper. But generally allow users to bring their own.
        - MS wrapper around DB
        - RESTful way to represent objects.
            - These objects are stored in the DB, and the uri to refer to them is passed around instead of the object itself.
- Add support for docker instances, rather than subprocess
    - And/or kubernetes etc.
- Add support for stateful MS (this is low priority, generally this shouldn't be needed, but there are a few exceptions like rate limiting)
    - Option on the `@microservice` decorator to tag as "stateful" - `@microservice(stateful=True)`
    - Some sort of transaction ID required.
    - Will need to quiesce on retirement of MS if it's tagged as a stateful MS

- Look into replacing the HTTP interconnection between MS's with ZeroMQ - sounds like it'll be faster/better/stronger


# Future improvements
These are mostly ideas that need thinking about a *lot*.

## Better Load Balancing
I think the current implementation of load balancing will actually serve for a long time - as long as a decent
way of dealing with robustness is implemented.

Any better solution should only be considered once a story about state is worked out.
Load balancers may have to be stateful in that model.

Currently there are 3 options:

 - No load balancing
 - Orchestration load balancing (orchestrator tells client about a single MS from a set)
 - Client load balancing (orchestrator tells client about all MS's and the client round robins)
    - This option actually scales really well, I think.

Future ideas include:
 - Independent load balancer
 - Docker swarm
 - kubernetes something?
 - ??


## Performance!
### Better options for parallel processing within each microservice
Current (or, at least, at time of writing) implementation uses a local pool of workers from the python `threading`
module. There are better alternatives:

- uWSGI (linux only)
    - Listens on given port (either HTTP or custom protocol uwsgi (yes, same name, sigh) which is better performance)
    - Farms out requests to N processes x M threads of a single-threaded flask app
    - comes with stats!
    - More performant
- gunicorn
- gevent



