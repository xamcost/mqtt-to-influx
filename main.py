"""
This script creates a MQTT client intended to connect to a home server mosquitto
broker and subscribe to all topics where home measurements data are published.
All received messages are formatted and dumped in an Influx DB.
"""

import datetime
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from zoneinfo import ZoneInfo

import paho.mqtt.client as mqttc
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Logging configuration
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s: %(message)s"
)
_logger = logging.getLogger(__name__)
logging.getLogger("").handlers = []
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)
_logger.addHandler(console_handler)

file_handler = RotatingFileHandler(
    f"/logs/{__name__}.log", maxBytes=500000000, backupCount=1
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)
_logger.addHandler(file_handler)

# MQTT Broker parameters
BROKER_HOST = os.getenv("BROKER_HOST")
BROKER_PORT = int(os.getenv("BROKER_PORT"))
BROKER_USER = os.getenv("BROKER_USER")
BROKER_PWD = os.getenv("BROKER_PWD")

# MQTT Topics to subscribe to
# BALCONY_TOPIC = "enviro/outdoor-balcony"
KITCHEN_TOPIC = "enviro/home-kitchen"
HS_SHTC3_TOPIC = "home/server/shtc3"
TOPICS = [
    # BALCONY_TOPIC,
    KITCHEN_TOPIC,
    HS_SHTC3_TOPIC,
]

# InfluxDB parameters
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")
INFLUX_CLIENT = None


def shift_timezone(timestamp, tz):
    """
    Shifts the timezone of a given string formatted UTC datetime.

    Parameters
    ----------
    timestamp : str
        The datetime to shift.
    tz : str
        The timezone to shift to.

    Returns
    -------
    datetime.datetime
        The shifted datetime object.
    """
    dt = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(ZoneInfo(tz))


def on_connect(client, userdata, flags, rc):
    """
    Callback for when the client receives a CONNACK response from the broker.
    Subscribes to all topics defined in the TOPICS list.

    Parameters
    ----------
    client : mqttc.Client
        The client instance for this callback.
    userdata : any
        The user data as passed to the Client() constructor or user_data_set().
    flags : dict
        Response flags sent by the broker.
    rc : int
        The connection result.
    """
    global INFLUX_CLIENT
    INFLUX_CLIENT = InfluxDBClient.from_env_properties()
    _logger.info(f"MQTT client connected to host {BROKER_HOST}:{BROKER_PORT}")
    for topic in TOPICS:
        client.subscribe(topic=topic)
        _logger.info(f"MQTT client subscribed to topic {topic}")


def on_disconnect(client, userdata, rc):
    """
    Callback for when the client disconnects from the broker.

    Parameters
    ----------
    client : mqttc.Client
        The client instance for this callback.
    userdata : any
        The user data as passed to the Client() constructor or user_data_set().
    rc : int
        The disconnection result.
    """
    INFLUX_CLIENT.close()
    _logger.info(f"MQTT client disconnected from host {BROKER_HOST}:{BROKER_PORT}")


def on_message(client, userdata, message):
    """
    Callback for when a message is sent to the broker in a topic the client is
    subscribed to. Indexes the message in Elasticsearch.

    Parameters
    ----------
    client : mqttc.Client
        The client instance for this callback.
    userdata : any
        The user data as passed to the Client() constructor or user_data_set().
    message : MQTTMessage
        An instance of MQTTMessage.
    """
    topic = message.topic
    _logger.info(f"Received message on topic {topic} with QoS {message.qos}.")
    content = json.loads(message.payload.decode("utf-8"))
    _logger.info(f"Message content: {content}")

    rec = None
    dt = shift_timezone(content["timestamp"], "Europe/Paris")
    # if topic == BALCONY_TOPIC:
    if topic == KITCHEN_TOPIC:
        rec = (
            Point("environment")
            .time(dt)
            # .tag("location", "balcony")
            .tag("location", "kitchen")
            .field("pm1", float(content["pm1"]))
            .field("pm2_5", float(content["pm2_5"]))
            .field("pm10", float(content["pm10"]))
            .field("temperature", float(content["temperature"]))
            .field("humidity", float(content["humidity"]))
            .field("pressure", float(content["pressure"]))
            .field("noise", float(content["noise"]))
        )
    elif topic == HS_SHTC3_TOPIC:
        rec = (
            Point("environment")
            .time(dt)
            .tag("location", "home-server")
            .field("temperature", float(content["temperature"]))
            .field("humidity", float(content["humidity"]))
        )

    if rec is not None:
        with INFLUX_CLIENT.write_api(write_options=SYNCHRONOUS) as influx_write:
            influx_write.write(bucket=INFLUX_BUCKET, record=rec)
        _logger.info(f"Message {rec} dumped in InfluxDB bucket {INFLUX_BUCKET}")
    else:
        _logger.warning("Message not dumped in InfluxDB")


if __name__ == "__main__":
    client = mqttc.Client(client_id=None, clean_session=True)
    client.enable_logger(logger=_logger)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    client.username_pw_set(username=BROKER_USER, password=BROKER_PWD)
    client.connect(host=BROKER_HOST, port=BROKER_PORT)

    try:
        client.loop_forever()
    finally:
        client.disconnect()
