# TODO

A set of pretty basic requirements that need implementing.
Generally aim to implement *something* with the expectation that it could be ripped out easily.
Learn and improve!


## featurelist

### next up
- automatic microservice discovery
    - Easy one is to import (and require import) of all modules where an MS is defined
    - is there a better way?

- test interface in:
    - zero mode
    - synchronous mode

- test concurrent requests (sync and async)
    - works when run manually
    - add automatic checks
    - thread locals are working (no bleeding over of requests)

- improve settings
    - improve idempotency for tests
        - maybe a "reset all" function
    - make settings settings again!
        - There shouldn't be functions in there?

- Add service discovery for interface to discover location of remote service in k8s deployment mode
    - because can't rely on k8s dns
    - may also want to have multiple locations (e.g. multiple hosts, local or remote)
- Test the ability to host the microservices in k8s, but the interface separately
    - that means we can't rely on k8s dns for routing.
    - Instead need to set the via headers in the message to the actual host and port.
    - Also want to support specifying the interface return address.

- define build/deployment process for actual users
    - for k8s
- Test EFK stack integration

- refactor to make the code structure make more sense
    - update docs
        - docstrings
        - help
        - design

### general
- Move to kubernetes
    - Define build process
    - (later) support multi-service pods (e.g. BYO datastore for the pod)
    - (later) support daemonsets for storage/stateful stuff
    - Add "external" flag to microservice decorator
        - The kubernetes Service for this will get exposed
- support openshift?
- support AWS?
- support azure?

- Resolve concurrent requests problem
    - actor model implemented - scale testing needed.
        - Advise users to put calls to other microservices at the top of the function, if possible.
    - probably also want gunicorn?


- Docs
    - Improve docstrings
    - Create examples
    - update README

- Improve exception handling
    - Currently, we get a bunch of catch/reraise frames added for each microservice that an exception travelled through
    - It would be nice for end users to strip out these exception frames, so they only see what is relevant to them
    - Overall, that means they'd see ~identical exceptions in ZERO and ACTOR modes
    - Note that jinja2 does something like this, I think: https://github.com/pallets/jinja/blob/5b498453b5898257b2287f14ef6c363799f1405a/jinja2/debug.py
        - It's horrible and hacky but... maybe worth it.

- Add storage
    - Short term "ephemeral" storage - fast access required
        - Also needs to serve as a cache for the slower long term storage
        - Probably a container running memcached
        - Cluster those containers using astaire
        - do we want to create an astaire cluster for each use case? i.e. one per stateful MS?
    - Long term storage - speed less key.
        - Probably an actual database - cassandra maybe? TBD
- Add performance tuning options
    - Minimum number of active services of a type
    - high/low congestion watermarks (percentage to scale up/down)
    - number of threads per microservice
    - enforce single process; and pin each microservice to a single core?
        - That's not really in the spirit of microservices
    - some way to characterise the max number of a given microservices per given host?
- Add multiple host support
    - support cloud burst
        - e.g. local servers, but expand to AWS when needed

- Security
    - Some sort of security - TLS? IPSec?
        - to outside internet
        - between every MS
- Robustness
    - Deal with individual MS's failing
        - re-run requests as MS level will end up chaining too much
        - maybe re-run request at the most outside scope
- object support?
    - Currently this only works for functions
    - do we want to make it work for objects?
        - essentially auto-convert an object to an API that grabs it's state from a database
            - has to lock the object in the DB, so doesn't help scalabilty of that object
            - but, pushes the robustness of stateful objects from the MS to the DB, so yes?
    - Needs:
        - DB service
            - Ship a sample DB and a sample wrapper. But generally allow users to bring their own.
        - MS wrapper around DB
        - RESTful way to represent objects.
            - These objects are stored in the DB, and the uri to refer to them is passed around instead of the object itself.

# WIBNIs

- Distributed logging direct to fluentd / logstash
    - log formatting done, but specific sinks of those logs untested:
        - test fluentd logging works
        - test logstash logging works


## Performance!
Test it! (needs AWS or similar)
