FROM python:3

WORKDIR /usr/src/app

COPY microservice /usr/src/app/microservice

RUN cd /usr/src/app/microservice \
 && pip install --no-cache-dir --upgrade -r requirements.txt

ENTRYPOINT ["/usr/local/bin/microservice", "--host", "0.0.0.0", "--port", "5000", "--service"]