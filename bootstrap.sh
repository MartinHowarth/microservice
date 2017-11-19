#!/usr/bin/env bash
minikube delete
minikube start
timeout 60
minikube addons enable heapster
minikube dashboard
timeout 60
minikube addons open heapster
# python microservice\bootstrap.py