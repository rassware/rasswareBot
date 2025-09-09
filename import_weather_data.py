# -*- coding: utf-8 -*-

import configparser
import datetime
import json
import os
import sqlite3
import paho.mqtt.client as mqtt

# Konfigurationsdatei einlesen
config = configparser.ConfigParser()
home_dir = os.path.expanduser('~')
credential_dir = os.path.join(home_dir, '.credentials')
config.read(os.path.join(credential_dir, 'weather_upload'))

MQTT_BROKER = config.get('MQTT', 'broker', fallback='localhost')
MQTT_PORT = config.getint('MQTT', 'port', fallback=1883)
MQTT_TOPIC = config.get('MQTT', 'topic', fallback='sensors/weather')


class SensorData:
    def __init__(self, data):
        self.time = datetime.datetime.strptime(data['time'], '%Y-%m-%d %H:%M:%S')
        self.model = data['model']
        self.sensor_id = data['id']
        self.channel = data.get('channel', "")
        self.temperature_C = ""
        self.temperature_C_dec = None
        self.humidity = ""
        self.humidity_dec = None

        if 'temperature_C' in data:
            self.temperature_C = str(data['temperature_C'])
            self.temperature_C_dec = data['temperature_C']
        if 'humidity' in data:
            self.humidity = str(data['humidity'])
            self.humidity_dec = data['humidity']
        if 'temperature_F' in data:
            self.temperature_C = (data['temperature_F'] - 32) * 5 / 9
            self.temperature_C_dec = float(self.temperature_C)

    def __str__(self):
        return ("time: %s, model: %s, sensor_id: %s, channel: %s, "
                "temperature_c: %s, temperature_c_dec: %s, "
                "humidity: %s, humidity_dec: %s") % (
            self.time, self.model, self.sensor_id, self.channel,
            self.temperature_C, self.temperature_C_dec,
            self.humidity, self.humidity_dec)

    def write_sensor_data(self):
        sql = """
        INSERT INTO sensors(
            time, model, sensor_id, channel,
            temperature_C, temperature_C_dec,
            humidity, humidity_dec
        ) VALUES (?,?,?,?,?,?,?,?)
        """
        with sqlite3.connect(config.get('Database', 'path', fallback='sensors.db')) as con:
            cur = con.cursor()
            cur.execute(sql,
                        (self.time, self.model, self.sensor_id,
                         self.channel, self.temperature_C,
                         self.temperature_C_dec, self.humidity,
                         self.humidity_dec))
            con.commit()


# MQTT Callback-Funktionen
def on_connect(client, userdata, flags, rc, properties=None):
    print("Verbunden mit MQTT Broker, Code:", rc)
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)
        sensor_data = SensorData(data)
        print("Empfangen:", sensor_data)
        sensor_data.write_sensor_data()
    except Exception as e:
        print("Fehler beim Verarbeiten der Nachricht:", e)


# MQTT Client starten
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()
