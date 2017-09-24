from microservice.development.functions import echo_as_dict2, echo_as_dict

if __name__ == "__main__":

    print("Echo as dict says: %s" % echo_as_dict2(1, 2, 3, apple=5, banana="cabbage"))
    print("Echo as dict says: %s" % echo_as_dict(4, 5, 6, apple=5, banana="cabbage"))
    print("Echo as dict says: %s" % echo_as_dict(4, 5, 6, apple=5, banana="cabbage"))
    print("Echo as dict says: %s" % echo_as_dict(4, 5, 6, apple=5, banana="cabbage"))
