# microservice

# Quickstart
## Minikube
Installation instructions here: https://github.com/kubernetes/minikube

### Windows
To get basic setup done:
```
minikube delete
minikube start --cpus 4 --memory 8192
timeout 60
minikube addons enable heapster
minikube addons enable efk
minikube dashboard
timeout 60
minikube addons open heapster
timeout 600
minikube addons open efk
```