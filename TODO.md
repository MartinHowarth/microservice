# TODO

A set of pretty basic requirements that need implementing.
Generally aim to implement *something* with the expectation that it could be ripped out easily.
Learn and improve!

- More automatic tests!
    - Healthchecking
    - Scaling up / down
- Additional testing:
    - More complicated import models
    - Interaction with other decorators
- Improve healthchecking:
    - all MS subscribe to the healthchecker MS
    - The MS's therefore know the healthchecker URI
    - MS's send regular heartbeats to the healthchecker
    - TBD what we do when we need to scale higher than one healthchecker can handle - there are many implementations out on the internet.
    - Deal with the case where a service is too congested to send a heartbeat in a timely manner
        - probably want to put non-responsive MS's in a quarantine for N time until they either start responding, or we declare them dead
        - Actually, it's simple: just flag it to die. It's either dead or as-good-as-dead.
- Make the pubsub system somehow find out about dead subscribers.
    - MS_A dies
    - S notices somehow? Or is told by O
- Deal with many concurrent requests better
    - E.g. imagine a function loop that calls into itself 1000 times before completing
    - We'd need 1000 handlers for that microservice
    - which right now, requires 1000 threads, of which (at the end) 999 of them are just blocking on another one)
    - Move to some sort of worker pool model? non-blocking requests to other microservices
        - ?????
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
    - Client gets notified about the services it wants to use.
    - This is the default option
    - This option actually scales really well, I think.
        - Better than an independent load balancer because that load balancer has to pass through every request
        - Worse because every user of MS_1 has to be notified about changes in the existence of MS's that they use.
            - This pub/sub system works, but really depends on how often we scale up/down individual instances.

Future ideas include:
 - Independent load balancer
 - Docker swarm
 - kubernetes something?
 - ??


## Better PubSub system
Home rolled very simple version at the moment.

This is actually only required for client-side load balancing, so think about any plans here in the context of what the right load
balancer solution is.

Look into moving to use a more generic open source (and therefore hopefully more field hardened) version, suggestions are:
 - crossbar


## Performance!
### Testing!
...

### Better options for parallel processing within each microservice
Current implementation (at least at time of writing) is just using Flask(threaded=True) and sideways scaling.
There are probably better alternatives:

- uWSGI (linux only)
    - Listens on given port (either HTTP or custom protocol uwsgi (yes, same name, sigh) which is better performance)
    - Farms out requests to N processes x M threads of a single-threaded flask app
    - comes with stats!
    - More performant
- gunicorn
- gevent



