# microservice

## Show me some examples!
See the example project here:
https://github.com/MartinHowarth/microservice_example_project

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

# CI
Test pipeline hosted here:
https://circleci.com/gh/MartinHowarth/microservice/

Dockerfile build hosted bere:
https://hub.docker.com/r/martinhowarth/microservice
