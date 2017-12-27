FROM python:3

WORKDIR /usr/src/app

COPY . /usr/src/app/microservice

RUN cd /usr/src/app/microservice \
 && python setup.py install

ENTRYPOINT ["/usr/local/bin/microservice", "--host", "0.0.0.0", "--port", "5000", "--service"]