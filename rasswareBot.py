# -*- coding: utf-8 -*-

import sys
import time
import datetime
import sqlite3
import telepot
import requests
import json
import plotly.plotly as py
import plotly.graph_objs as go
from random import randint
import configparser
from os.path import expanduser
# https://github.com/nickoala/telepot/issues/87#issuecomment-235173302
import telepot.api
import urllib3
import subprocess
import traceback
import logging

telepot.api._pools = {
    'default': urllib3.PoolManager(num_pools=3, maxsize=10, retries=3, timeout=30),
}


def force_independent_connection(req, **user_kw):
    return None


telepot.api._which_pool = force_independent_connection

config = configparser.RawConfigParser()
home = expanduser("~")
config.read(home + "/.credentials/rasswareBotConfig")

DATEFORMAT = config.get('rasswareBot', 'dateformat')
DATABASE = config.get('Database', 'path')
ADMINCHATID = int(config.get('Telegram', 'adminchatid'))
WEBCAMIMAGE = config.get('rasswareBot', 'webcamimage')
AUDIOFILE = config.get('rasswareBot', 'audiofile')
OUTDOORSENSORID = config.get('rasswareBot', 'outdoorsensorid')

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)

class DataProvider:
    tempField = "temperature_C_dec"
    humiField = "humidity_dec"
    lastCheck = datetime.datetime.now()
    lastOpenWeatherCheck = None

    def getLastValues(self, field):
        sql = "select model, sensor_id, time, {0} from sensors where id in (select max(id) from sensors where time between datetime(CURRENT_TIMESTAMP, '-6 hour', 'localtime') and datetime(CURRENT_TIMESTAMP, 'localtime') and {0} is not null and sensor_id > 0 group by sensor_id);".format(
            field)
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        a = cur.execute(sql)
        data = []
        if a == 0:
            data.extend("Keine Klimadaten gefunden!")
        else:
            for row in cur.fetchall():
                messzeit = datetime.datetime.strptime(str(row[2]), DATEFORMAT).strftime('%H:%M:%S')
                sensor = str(row[0])
                id = row[1]
                value = float(row[3])
                data.append([sensor, id, messzeit, value])
        con.close()
        return data

    def getLastNightTemperatures(self):
        sql = """select model, sensor_id, min(temperature_C_dec), max(temperature_C_dec) from sensors where 
				 time between datetime(date(CURRENT_TIMESTAMP, '-1 day'), '20:00:00') and datetime(date(CURRENT_TIMESTAMP), '08:00:00') and
				 temperature_C_dec is not null and sensor_id > 0
				 group by sensor_id"""
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        a = cur.execute(sql)
        data = []
        if a == 0:
            data.extend("Keine Klimadaten gefunden!")
        else:
            for row in cur.fetchall():
                minValue = float(row[2])
                sensor = str(row[0])
                id = row[1]
                maxValue = float(row[3])
                data.append("{0}[{1}]\nmin: {2}{4} max: {3}{4}".format(sensor, id, minValue, maxValue, " °C"))
        con.close()
        return data

    def getLastTemperatures(self):
        result = []
        label = " °C"
        data = self.getLastValues(self.tempField)
        for i in data:
            result.append("{0}[{1}]\n{2}: {3}{4}".format(i[0], i[1], i[2], i[3], label))
        return result

    def getLastHumidities(self):
        result = []
        label = " %"
        data = self.getLastValues(self.humiField)
        for i in data:
            result.append("{0}[{1}]\n{2}: {3}{4}".format(i[0], i[1], i[2], i[3], label))
        return result

    def checkForFrost(self, sensor_id):
        data = self.getLastValues(self.tempField)
        for item in data:
            if item[3] < float(config.get('rasswareBot', 'frosttriggertemp')) and str(sensor_id) == str(item[1]):
                logging.info("Frost da! {0} °C, gemessen von sensor_id {1}".format(item[3], item[1]))
                return True
        return False

    def registerForAlert(self, chatId, sensor_id):
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute("INSERT OR IGNORE INTO registered(chatid, sensor_id) VALUES ({0}, {1});".format(chatId, sensor_id))
        con.commit()
        con.close()

    def unregisterForAlert(self, chatId, sensor_id):
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute("DELETE FROM registered WHERE chatid = {0} and sensor_id = {1};".format(chatId, sensor_id))
        con.commit()
        con.close()

    def updateLastAlert(self, chatId, sensor_id, last_alert):
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute(
            "UPDATE registered SET last_alert = '{0}' WHERE chatid = {1} and sensor_id = {2};".format(last_alert,
                                                                                                      chatId,
                                                                                                      sensor_id))
        con.commit()
        con.close()

    def getRegistered(self):
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute("SELECT chatid, sensor_id, last_alert FROM registered;")
        data = []
        for row in cur.fetchall():
            last_alert = datetime.datetime.strptime(str(row[2]), DATEFORMAT) if row[2] != None else None
            data.append([int(row[0]), row[1], last_alert])
        con.close()
        return data

    def getWeatherInfo(self):
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute(
            "SELECT description,pressure,wind_speed,wind_deg,sunrise,sunset,datetime(date_created, 'localtime') FROM open_weather ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        description = row[0]
        pressure = float(row[1])
        wind_speed = float(row[2])
        wind_deg = float(row[3])
        sunrise = datetime.datetime.strptime(str(row[4]), DATEFORMAT).strftime('%H:%M:%S')
        sunset = datetime.datetime.strptime(str(row[5]), DATEFORMAT).strftime('%H:%M:%S')
        date_created = str(row[6])
        con.close()
        return "Wetterdaten von {0}\n{1}\nLuftdruck: {2} hPa\nWindstärke: {3} m/s\nWindrichtung: {4}°\nSonnenaufgang: {5}\nSonnenuntergang: {6}".format(
            date_created, description, pressure, wind_speed, wind_deg, sunrise, sunset)

    def queryOpenWeather(self):
        self.lastOpenWeatherCheck = datetime.datetime.now()
        url = "https://api.openweathermap.org/data/2.5/weather?id={}&lang=de&units=metric&APPID={}".format(
            config.get('OpenWeatherMap', 'cityid'), config.get('OpenWeatherMap', 'key'))
        response = requests.post(url)
        logging.info("Query OpenWeather API ...")
        try:
            data = json.loads(response.text)
            con = sqlite3.connect(DATABASE)
            cur = con.cursor()
            description = str(data['weather'][0].get('description', 'no data'))
            pressure = data['main'].get('pressure', 0)
            wind_speed = data['wind'].get('speed', 0)
            wind_deg = data['wind'].get('deg', 0)
            sunrise = data['sys'].get('sunrise', datetime.datetime.now())
            sunset = data['sys'].get('sunset', datetime.datetime.now())
            cur.execute(
                "INSERT INTO open_weather(description,pressure,wind_speed,wind_deg,sunrise,sunset) VALUES ('{0}',{1},{2},{3},datetime({4},'unixepoch','localtime'),datetime({5},'unixepoch','localtime'))".format(description, pressure, wind_speed, wind_deg, sunrise, sunset))
            con.commit()
            con.close()
        except ValueError:
            logging.info("Could not query OpenWeater API")

    def sendOpenWeather(self):
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute(
            "SELECT temperature_C_dec FROM sensors WHERE sensor_id = '" + OUTDOORSENSORID + "' AND temperature_C_dec IS NOT NULL ORDER BY ID DESC LIMIT 1")
        row = cur.fetchone()
        temp = row[0]
        cur.execute(
            "SELECT humidity_dec FROM sensors WHERE sensor_id = '" + OUTDOORSENSORID + "' AND humidity_dec IS NOT NULL ORDER BY ID DESC LIMIT 1")
        row = cur.fetchone()
        humi = row[0]
        con.close()
        station_id = config.get('OpenWeatherMap', 'stationid')
        data = json.dumps([{"station_id": station_id, "dt": int(time.time()), "temperature": temp, "humidity": humi}])
        response = requests.post('http://api.openweathermap.org/data/3.0/measurements?APPID={}'.format(config.get('OpenWeatherMap', 'key')), data=data, headers={"Content-Type": "application/json"})
        logging.info("send data to OpenWeather API: " + str(response.status_code))

    def sendWetterArchiv(self):
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute(
            "SELECT temperature_C_dec FROM sensors WHERE sensor_id = '" + OUTDOORSENSORID + "' AND temperature_C_dec IS NOT NULL ORDER BY ID DESC LIMIT 1")
        row = cur.fetchone()
        temp = row[0]
        cur.execute(
            "SELECT humidity_dec FROM sensors WHERE sensor_id = '" + OUTDOORSENSORID + "' AND humidity_dec IS NOT NULL ORDER BY ID DESC LIMIT 1")
        row = cur.fetchone()
        humi = row[0]
        con.close()
        id = config.get('WetterArchiv', 'id')
        pwd = config.get('WetterArchiv', 'pwd')
        sid = config.get('WetterArchiv', 'sid')
        dtutc = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        data = {'id': id, 'pwd': pwd, 'sid': sid, 'dtutc': dtutc, 'te': temp, 'hu': humi}
        response = requests.get('https://interface.wetterarchiv.de/weather', params=data)
        logging.info("send data to WetterArchiv API: " + response.text)

    def getPressureHistory(self, limit):
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute("SELECT date_created,pressure FROM open_weather ORDER BY id DESC LIMIT {0}".format(limit))
        data = cur.fetchall()
        con.close()
        return data

    def getSensors(self):
        result = []
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute(
            "SELECT sensor_id, model FROM sensors WHERE time > datetime('now', '-24 hour') GROUP BY sensor_id ORDER BY model;")
        for row in cur.fetchall():
            if row[0]:
                result.append("/data_{1}_3 - {0}".format(row[1], row[0]))
        con.close()
        return result

    def getSensorData(self, sensorid, limit):
        temps = []
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute(
            "SELECT time, temperature_C_dec FROM sensors where sensor_id = {0} AND temperature_C_dec IS NOT NULL ORDER BY time DESC limit {1}".format(
                sensorid, limit))
        for row in cur.fetchall():
            temps.append("{0}: {1} °C".format(row[0], row[1]))
        humis = []
        cur = con.cursor()
        cur.execute(
            "SELECT time, humidity_dec FROM sensors where sensor_id = {0} AND humidity_dec IS NOT NULL ORDER BY time DESC limit {1}".format(
                sensorid, limit))
        for row in cur.fetchall():
            humis.append("{0}: {1} %".format(row[0], row[1]))
        con.close()
        result = []
        result.append("Temperatur:")
        result.extend(temps)
        result.append("Luftfeuchte:")
        result.extend(humis)
        return result

    def recordAudio(self, length):
        arecord = ('arecord -Dplughw:1,0 -traw -fS16_LE -r48k -d'+str(length)).split()
        sox = 'sox -traw -r48k -es -b16 -c1 -V1 - -tmp3 -'.split()
        with open(AUDIOFILE, "w") as f:
            arecord_process = subprocess.Popen(arecord, stdout=subprocess.PIPE)
            sox_process = subprocess.Popen(sox, stdin=arecord_process.stdout, stdout=subprocess.PIPE)
            output = sox_process.communicate()[0]
            f.write(output)
            f.flush()


prov = DataProvider()
errorMsg = "Das habe ich nicht verstanden ..."
helpMsg = """
/lastTemp - Liefert aktuelle Temperaturwerte
/lastHumi - Liefert aktuelle Luftfeuchtigkeitswerte
/lastNightTemp - Liefert die MIN/MAX Temperaturen der letzten Nacht
/pressure <limit> - Liefert historische Luftdruckwerte
/graph_<limit> - Zeichnet ein Luftdruckdiagramm
/sensors - Liefert die Ids der Sensoren
/data <sensorid> <limit> - Liefert Daten für einen Sensor
/register <sensor_id> - Für den Frostalarm anmelden
/unregister <sensor_id> - Für den Frostalarm abmelden
/weather - Allgemeine Wetterdaten
"""


def handle(msg):
    chat_id = msg['chat']['id']
    command = msg['text']
    logging.info('Got command: %s' % command)
    if command == '/lastTemp':
        bot.sendMessage(chat_id, "\n".join(prov.getLastTemperatures()))
    elif command == '/lastHumi':
        bot.sendMessage(chat_id, "\n".join(prov.getLastHumidities()))
    elif command == '/lastNightTemp':
        bot.sendMessage(chat_id, "\n".join(prov.getLastNightTemperatures()))
    elif command == '/weather':
        bot.sendMessage(chat_id, prov.getWeatherInfo() + "\n" + "\n".join(prov.getLastTemperatures()))
    elif command.startswith('/pressure'):
        args = command.split(' ', 1)
        limit = int(args[-1]) if args[-1].isdigit() else 10
        if len(args) > 2 or limit > 100:
            bot.sendMessage(chat_id, "Syntax: \"/pressure <limit>\"\nLimit max 100")
        else:
            result = []
            data = prov.getPressureHistory(limit)
            for row in data:
                result.append("{0}: {1} hPa".format(str(row[0]), float(row[1])))
            bot.sendMessage(chat_id, "\n".join(result))
    elif command.startswith('/graph'):
        args = command.split('_', 1)
        limit = int(args[-1]) if args[-1].isdigit() else 10
        if len(args) > 2 or limit > 100:
            bot.sendMessage(chat_id, "Syntax: \"/graph_<limit>\"\nLimit max 100")
        else:
            x = []
            y = []
            data = prov.getPressureHistory(limit)
            for row in data:
                x.append(str(row[0]))
                y.append(float(row[1]))
            chartdata = [go.Scatter(x=x, y=y)]
            url = py.plot(chartdata, filename='pressure') + ".png?v=" + str(randint(0, 25000))
            bot.sendPhoto(chat_id, url)
    elif command.startswith('/register'):
        args = command.split(' ', 1)
        sensor_id = str(args[-1])
        if len(args) > 2 or sensor_id.isdigit() == False:
            bot.sendMessage(chat_id, "Syntax: \"/register <sensor_id>\"")
        else:
            prov.registerForAlert(chat_id, sensor_id)
            bot.sendMessage(chat_id, "Erfolgreich registriert!")
    elif command.startswith('/unregister'):
        args = command.split(' ', 1)
        sensor_id = str(args[-1])
        if len(args) > 2 or sensor_id.isdigit() == False:
            bot.sendMessage(chat_id, "Syntax: \"/unregister <sensor_id>\"")
        else:
            prov.unregisterForAlert(chat_id, sensor_id)
            bot.sendMessage(chat_id, "Erfolgreich abgemeldet!")
    elif command == "/sensors":
        bot.sendMessage(chat_id, "\n".join(prov.getSensors()))
    elif command.startswith('/data'):
        args = command.split('_', 2)
        sensorid = str(args[1])
        limit = int(args[-1]) if args[-1].isdigit() else 3
        if len(args) > 3 or limit > 100 or not sensorid:
            bot.sendMessage(chat_id, "Syntax: \"/data_<sensorid>_<limit>\"\nLimit max 100")
        else:
            bot.sendMessage(chat_id, "\n".join(prov.getSensorData(sensorid, limit)))
    elif command == "/help":
        bot.sendMessage(chat_id, helpMsg + "/webcam - Webcam Bild\n/audio <sec> - Audio" if chat_id == ADMINCHATID else helpMsg)
    elif command == "/webcam" and chat_id == ADMINCHATID:
        f = open(WEBCAMIMAGE, 'rb')
        bot.sendPhoto(ADMINCHATID, f)
    elif command.startswith('/audio') and chat_id == ADMINCHATID:
        args = command.split(' ', 2)
        if args[1].isdigit():
            length = int(args[1])
        else:
            length = 30
        prov.recordAudio(length)
        f = open(AUDIOFILE, 'rb')
        bot.sendAudio(ADMINCHATID, f)
    else:
        bot.sendMessage(chat_id, errorMsg)

    flavor = telepot.flavor(msg)

    summary = telepot.glance(msg, flavor=flavor)
    logging.info(flavor, summary)


bot = telepot.Bot(config.get('Telegram', 'token'))
bot.message_loop(handle)
logging.info('Listening ...')

# Keep the program running.
while 1:
    try:
        time.sleep(10)
        if prov.lastOpenWeatherCheck == None:
            prov.queryOpenWeather()
            prov.sendOpenWeather()
            prov.sendWetterArchiv()
        if datetime.datetime.now() > prov.lastOpenWeatherCheck + datetime.timedelta(
                minutes=int(config.get('OpenWeatherMap', 'interval'))):
            prov.queryOpenWeather()
            prov.sendOpenWeather()
            prov.sendWetterArchiv()

        if datetime.datetime.now() > prov.lastCheck + datetime.timedelta(
                minutes=int(config.get('rasswareBot', 'frostcheckinterval'))):
            prov.lastCheck = datetime.datetime.now()
            for registered in prov.getRegistered():
                chat_id = registered[0]
                sensor_id = registered[1]
                last_alert = registered[2]
            if prov.checkForFrost(sensor_id) == True and (
                    last_alert == None or datetime.datetime.now() > last_alert + datetime.timedelta(
                    minutes=int(config.get('rasswareBot', 'frostalertdelay')))):
                prov.updateLastAlert(chat_id, sensor_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                bot.sendMessage(chat_id, "FROSTWARNUNG!!!111elf\n{}".format("\n".join(prov.getLastTemperatures())))
    except Exception as e:
        logging.error(e.__doc__)
        logging.error(e)
        logging.error(traceback.format_exc())
db.close()
