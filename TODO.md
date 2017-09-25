## TODO

In no particular order, though somewhat higher priority towards the top

- Automatic test suite
- Additional testing:
    - More complicated import models
    - Interaction with other decorators
- Add robustness to the MS requests - deal with requests failing, and retry (expecting that the health checker will have recovered it)
- Add object support
    - Currently this only works for functions
    - Can we make it work for objects too?
    - Needs:
        - DB service
            - Ship a sample DB and a sample wrapper. But generally allow users to bring their own.
        - MS wrapper around DB
        - RESTful way to represent objects.
            - These objects are stored in the DB, and the uri to refer to them is passed around instead of the object itself.
- Add health checking
    - Is it alive? -> recreate
    - Add resource usage monitoring
        - If average exceeds 50?% then add another instance (or many, if the usage is sufficiently high?)
        - If average decreases below 30?% then remove an instance
            - Will need to quiesce if it's tagged as a stateful MS
- Add support for docker instances, rather than subprocess
    - And/or kubernetes etc.
- Add support for stateful MS (this is low priority, generally this shouldn't be needed, but there are a few exceptions like rate limiting)
    - Option on the `@microservice` decorator to tag as "stateful" - `@microservice(stateful=True)`
    - Some sort of transaction ID required.



# Future improvements
These mostly need thinking about a *lot*

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
