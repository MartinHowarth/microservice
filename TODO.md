## TODO

In no particular order, though somewhat higher priority towards the top

- Automatic test suite
- Additional testing:
    - More complicated import models
    - Interaction with other decorators
- Improved example: put varying length sleeps in some functions to show off sideways scaling
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
- Add load balancing
    - Three implementations come to mind:
        - Simple round-robin or random within the single orchestrator
        - Explicit load balancer based on this framework and the orchestrator references just that
            - If we've done the REST interface right, this should slot right in without any problems.
        - Docker swarm
        - ??
    - Must respect stateful MS's
- Add support for docker instances, rather than subprocess
    - And/or kubernetes etc.
- Add support for stateful MS (this is low priority, generally this shouldn't be needed, but there are a few exceptions like rate limiting)
    - Option on the `@microservice` decorator to tag as "stateful" - `@microservice(stateful=True)`
    - Some sort of transaction ID required.