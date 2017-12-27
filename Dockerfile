FROM python:3

WORKDIR /usr/src/app

COPY microservice .

RUN cd microservice \
 && pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["/usr/local/bin/microservice", "--host", "0.0.0.0", "--port", "5000", "--service"]