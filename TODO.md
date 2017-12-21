# TODO

A set of pretty basic requirements that need implementing.
Generally aim to implement *something* with the expectation that it could be ripped out easily.
Learn and improve!


## featurelist

### next up
- docker build process
- Distributed logging
- interface from non-MS to MS
    - e.g. translation from standard HTTP API to this message-based microservices api
- auto-deploy microservices (for deployment to k8s)

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

# Future improvements
These are mostly ide


## Performance!
Test it! (needs AWS or similar)
