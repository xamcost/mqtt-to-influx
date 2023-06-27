# mqtt-to-influx

A small containerized app intended to get messages from an MQTT broker and
dump them in an Influx DB. 

## How to use

As much as possible, this app has been made to be agnostic of the MQTT broker
and the configuration of the Influx DB, but it would need some customization
to fit your needs. You can set the location and the credentials of the broker
and database in environment variables, yet you will most likely have to
rewrite the `on_message` function in the `main` module, to convert the
MQTT payload into something dumpeable in the Influx DB. So basically, feel
free to fork this repo, do your modifications and rebuild the Docker image to
push it to your own registry.

## Personal use case

Just for the sake of completeness, I use this app in my home server, which is a
Kubernetes cluster of Raspberry Pis, to gather data from sensors at home
(temperature, humidity, ...). At time of writing, the `on_message` function
is designed to listen messages published by an
[Enviro Urban board](https://shop.pimoroni.com/products/enviro-urban?variant=40056508219475).
With time, I will add more sensors, and update this function accordingly.
