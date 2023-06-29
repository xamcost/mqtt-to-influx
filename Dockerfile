# 
FROM python@sha256:71afed5910cdec96814776079578269e194088a06a64952daebf0d745c1f105d

#
ENV BROKER_HOST="http://mosquitto.mosquitto.svc.cluster.local"
ENV BROKER_PORT=1883
ENV BROKER_USER=""
ENV BROKER_PWD=""
ENV INFLUXDB_V2_URL="http://influxdb.influxdb.svc.cluster.local:8086"
ENV INFLUXDB_V2_TOKEN=""
ENV INFLUXDB_V2_ORG=""
ENV INFLUX_BUCKET=""

# 
WORKDIR /code

#
COPY ./requirements.txt /code/requirements.txt

# 
RUN echo "[INFO] Creating logs directory ..." && \
    mkdir /logs && \
    echo "[INFO] Installing python requirements ..." && \
    pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 
COPY ./main.py /code/main.py

# 
CMD ["python", "/code/main.py"]
