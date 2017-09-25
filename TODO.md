# TODO

A set of pretty basic requirements that need implementing.
Generally aim to implement *something* with the expectation that it could be ripped out easily.
Learn and improve!

- Automatic test suite
- Additional testing:
    - More complicated import models
    - Interaction with other decorators
- Add robustness to the MS requests - deal with requests failing, and retry (expecting that the health checker will have recovered it)
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
- Add scaling
    - Add resource usage monitoring
        - If average exceeds 50?% then add another instance (or many, if the usage is sufficiently high?)
        - If average decreases below 30?% then remove an instance
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
    - This option actually scales really well, I think.

Future ideas include:
 - Independent load balancer
 - Docker swarm
 - kubernetes something?
 - ??
