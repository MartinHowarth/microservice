#! /bin/sh
minikube delete
minikube start
python microservice\bootstrap.py