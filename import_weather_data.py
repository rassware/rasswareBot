# -*- coding: utf-8 -*-

import ConfigParser
import datetime
import json
import os
import sqlite3

directory = '/home/crassmann/transfer/'

config = ConfigParser.ConfigParser()
home_dir = os.path.expanduser('~')
credential_dir = os.path.join(home_dir, '.credentials')
config.read(os.path.join(credential_dir, 'weather_upload'))


class SensorData:
    def __init__(self, data):
        self.time = datetime.datetime.strptime(data['time'], '%Y-%m-%d %H:%M:%S')
        self.model = data['model']
        self.sensor_id = data['id']
        self.channel = ""
        self.temperature_C = ""
        self.temperature_C_dec = ""
        self.humidity = ""
        self.humidity_dec = ""
        if 'channel' in data.keys():
            self.channel = data['channel']
        if 'temperature_C' in data.keys():
            self.temperature_C = str(data['temperature_C'])
            self.temperature_C_dec = data['temperature_C']
        if 'humidity' in data.keys():
            self.humidity = str(data['humidity'])
            self.humidity_dec = data['humidity']
        if 'temperature_F' in data.keys():
            self.temperature_C = (data['temperature_F'] - 32) * 5 / 9
            self.temperature_C_dec = float((data['temperature_F'] - 32) * 5 / 9)

    def __str__(self):
        return "time: %s, model: %s, sensor_id: %s, channel: %s, temperature_c: %s, temperature_c_dec: %s, humidity: %s, humidity_dec: %s" % (
            self.time, self.model, self.sensor_id, self.channel, self.temperature_C, self.temperature_C_dec, self.humidity, self.humidity_dec)

    def write_sensor_data(self):
        sql = """
        INSERT INTO sensors('time','model','sensor_id','channel','temperature_C','temperature_C_dec','humidity','humidity_dec') VALUES (?,?,?,?,?,?,?,?)
        """
        with sqlite3.connect(config.get('Database', 'path', 1)) as con:
            cur = con.cursor()
            cur.execute(sql,
                        (self.time, self.model, self.sensor_id, self.channel, self.temperature_C, self.temperature_C_dec, self.humidity, self.humidity_dec))
            con.commit()


for filename in os.listdir(directory):
    if filename.endswith(".json"):
        file = os.path.join(directory, filename)
        lines = tuple(open(file, 'r'))
        for line in lines:
            data = json.loads(line)
            sensor_data = SensorData(data)
            sensor_data.write_sensor_data()
        os.remove(file)
