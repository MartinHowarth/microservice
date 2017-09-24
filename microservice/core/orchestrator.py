

class Orchestrator:
    """
    This is a microservice that provides function to other microservices of:
        - Dicoverability of existing microservices
        - Creation of non-existent microservices
        - Health monitoring of microservices
        - Scaling of microservices

    """
    # An instance of a MS *is* a resource, so refer to it as a uri.
    # services = defaultdict(lambda: ['http://127.0.0.1:5000/microservice.development.functions.echo_as_dict'])
    # Is actually itself a MS

