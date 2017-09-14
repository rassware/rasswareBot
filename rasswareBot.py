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
import ConfigParser
from os.path import expanduser
# https://github.com/nickoala/telepot/issues/87#issuecomment-235173302
import telepot.api
import urllib3

telepot.api._pools = {
    'default': urllib3.PoolManager(num_pools=3, maxsize=10, retries=3, timeout=30),
}

def force_independent_connection(req, **user_kw):
    return None

telepot.api._which_pool = force_independent_connection

config = ConfigParser.ConfigParser()
home = expanduser("~")
config.read(home + "/.rasswareBotConfig")

DATEFORMAT = config.get('rasswareBot', 'dateformat', 1)
DATABASE = config.get('Database', 'path', 1)
ADMINCHATID = int(config.get('Telegram', 'adminchatid', 1))
WEBCAMIMAGE = config.get('rasswareBot', 'webcamimage', 1)

class DataProvider:

    tempField = "temperature_C_dec"
    humiField = "humidity_dec"
    lastCheck = datetime.datetime.now()
    lastOpenWeatherCheck = None

    def getLastValues(self,field):
        sql = "select model, sensor_id, time, {0} from sensors where id in (select max(id) from sensors where time between datetime(CURRENT_TIMESTAMP, '-6 hour', 'localtime') and datetime(CURRENT_TIMESTAMP, 'localtime') and {0} is not null and sensor_id > 0 group by sensor_id);".format(field)
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
                id = int(row[1])
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
                id = int(row[1])
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
                print "Frost da! {0} °C, gemessen von sensor_id {1}".format(item[3], item[1])
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
        cur.execute("UPDATE registered SET last_alert = '{0}' WHERE chatid = {1} and sensor_id = {2};".format(last_alert, chatId, sensor_id))
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
        cur.execute("SELECT description,pressure,wind_speed,wind_deg,sunrise,sunset,datetime(date_created, 'localtime') FROM open_weather ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        description = row[0].encode('utf-8')
        pressure = float(row[1])
        wind_speed = float(row[2])
        wind_deg = float(row[3])
        sunrise = datetime.datetime.strptime(str(row[4]), DATEFORMAT).strftime('%H:%M:%S')
        sunset = datetime.datetime.strptime(str(row[5]), DATEFORMAT).strftime('%H:%M:%S')
        date_created = str(row[6])
        con.close()
        return "Wetterdaten von {0}\n{1}\nLuftdruck: {2} hPa\nWindstärke: {3} m/s\nWindrichtung: {4}°\nSonnenaufgang: {5}\nSonnenuntergang: {6}".format(date_created,description,pressure,wind_speed,wind_deg,sunrise,sunset)

    def queryOpenWeather(self):
        self.lastOpenWeatherCheck = datetime.datetime.now()
        url = "http://api.openweathermap.org/data/2.5/weather?id={}&lang=de&units=metric&APPID={}".format(config.get('OpenWeatherMap', 'cityid', 1), config.get('OpenWeatherMap', 'key', 1))
        response = requests.post(url)
        print "Query OpenWeather API ..."
        try:
            data = json.loads(response.text)
            con = sqlite3.connect(DATABASE)
            cur = con.cursor()
            description = data['weather'][0].get('description', 'no data').encode('utf8')
            pressure = data['main'].get('pressure', 0)
            wind_speed =  data['wind'].get('speed', 0)
            wind_deg = data['wind'].get('deg', 0)
            sunrise = data['sys'].get('sunrise', datetime.datetime.now())
            sunset = data['sys'].get('sunset', datetime.datetime.now())
            cur.execute("INSERT INTO open_weather(description,pressure,wind_speed,wind_deg,sunrise,sunset) VALUES ('{0}',{1},{2},{3},datetime({4},'unixepoch','localtime'),datetime({5},'unixepoch','localtime'))".format(description, pressure, wind_speed, wind_deg, sunrise, sunset))
            con.commit()
            con.close()
        except ValueError:
            print "Could not query OpenWeater API"

    def sendOpenWeather(self):
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute("SELECT temperature_C_dec FROM sensors WHERE sensor_id = '3' AND temperature_C_dec IS NOT NULL ORDER BY ID DESC LIMIT 1")
        row = cur.fetchone()
        temp = row[0]
        cur.execute("SELECT humidity_dec FROM sensors WHERE sensor_id = '3' AND humidity_dec IS NOT NULL ORDER BY ID DESC LIMIT 1")
        row = cur.fetchone()
        humi = row[0]
        con.close()
        lat = config.get('OpenWeatherMap', 'lat')
        lng = config.get('OpenWeatherMap', 'lng')
        alt = config.get('OpenWeatherMap', 'alt')
        name = config.get('OpenWeatherMap', 'name', 1)
        user = config.get('OpenWeatherMap', 'user', 1)
        pw = config.get('OpenWeatherMap', 'pw', 1)
        data = {'temp': temp, 'humidity': humi, 'lat': lat, 'long': lng, 'alt': alt, 'name': name}
        response = requests.post('http://openweathermap.org/data/post', data, auth=(user, pw))
        print "send data to OpenWeather API: " + response.text

    def sendWetterArchiv(self):
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute("SELECT temperature_C_dec FROM sensors WHERE sensor_id = '3' AND temperature_C_dec IS NOT NULL ORDER BY ID DESC LIMIT 1")
        row = cur.fetchone()
        temp = row[0]
        cur.execute("SELECT humidity_dec FROM sensors WHERE sensor_id = '3' AND humidity_dec IS NOT NULL ORDER BY ID DESC LIMIT 1")
        row = cur.fetchone()
        humi = row[0]
        con.close()
        id = config.get('WetterArchiv', 'id')
        pwd = config.get('WetterArchiv', 'pwd')
        sid = config.get('WetterArchiv', 'sid')
        dtutc = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        data = {'id': id, 'pwd': pwd, 'sid': sid, 'dtutc': dtutc, 'te': temp, 'hu': humi}
        response = requests.get('http://interface.wetterarchiv.de/weather', params=data)
        print "send data to WetterArchiv API: " + response.text

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
	cur.execute("SELECT sensor_id, model FROM sensors where time > datetime('now', '-24 hour') GROUP BY sensor_id ORDER BY model;")
	for row in cur.fetchall():
	    if row[0]:
                result.append("/data_{1}_3 - {0}".format(row[1], row[0]))	    
	con.close()
	return result

    def getSensorData(self, sensorid, limit):
	temps = []
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
	cur.execute("SELECT time, temperature_C_dec FROM sensors where sensor_id = {0} AND temperature_C_dec IS NOT NULL ORDER BY time DESC limit {1}".format(sensorid, limit))
	for row in cur.fetchall():
	    temps.append("{0}: {1} °C".format(row[0], row[1]))
	humis = []
	cur = con.cursor()
        cur.execute("SELECT time, humidity_dec FROM sensors where sensor_id = {0} AND humidity_dec IS NOT NULL ORDER BY time DESC limit {1}".format(sensorid, limit))
	for row in cur.fetchall():
	    humis.append("{0}: {1} %".format(row[0], row[1]))
	con.close()
	result = []
	result.append("Temperatur:")
	result.extend(temps)
	result.append("Luftfeuchte:")
	result.extend(humis)
	return result

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
    print 'Got command: %s' % command
    if command == '/lastTemp':
        bot.sendMessage(chat_id, "\n".join(prov.getLastTemperatures()))
    elif command == '/lastHumi':
        bot.sendMessage(chat_id, "\n".join(prov.getLastHumidities()))
    elif command == '/lastNightTemp':
        bot.sendMessage(chat_id, "\n".join(prov.getLastNightTemperatures()))
    elif command == '/weather':
        bot.sendMessage(chat_id, prov.getWeatherInfo() + "\n" + "\n".join(prov.getLastTemperatures()))
    elif command.startswith('/pressure'):
        args = command.split(' ',1)
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
        args = command.split('_',1)
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
            url = py.plot(chartdata, filename = 'pressure') + ".png?v=" + str(randint(0,25000))
            bot.sendPhoto(chat_id, url)
    elif command.startswith('/register'):
        args = command.split(' ',1)
        sensor_id = str(args[-1])
        if len(args) > 2 or sensor_id.isdigit() == False:
            bot.sendMessage(chat_id, "Syntax: \"/register <sensor_id>\"")
        else:
            prov.registerForAlert(chat_id, sensor_id)
            bot.sendMessage(chat_id, "Erfolgreich registriert!")
    elif command.startswith('/unregister'):
        args = command.split(' ',1)
        sensor_id = str(args[-1])
        if len(args) > 2 or sensor_id.isdigit() == False:
            bot.sendMessage(chat_id, "Syntax: \"/unregister <sensor_id>\"")
        else:
            prov.unregisterForAlert(chat_id, sensor_id)
            bot.sendMessage(chat_id, "Erfolgreich abgemeldet!")
    elif command == "/sensors":
        bot.sendMessage(chat_id, "\n".join(prov.getSensors()))
    elif command.startswith('/data'):
	args = command.split('_',2)
	sensorid = str(args[1])
        limit = int(args[-1]) if args[-1].isdigit() else 3
        if len(args) > 3 or limit > 100 or not sensorid:
            bot.sendMessage(chat_id, "Syntax: \"/data_<sensorid>_<limit>\"\nLimit max 100")
        else:
	    bot.sendMessage(chat_id, "\n".join(prov.getSensorData(sensorid, limit)))
    elif command == "/help":
        bot.sendMessage(chat_id, helpMsg + "/webcam - Webcam Bild" if chat_id == ADMINCHATID else helpMsg)
    elif command == "/webcam" and chat_id == ADMINCHATID:
        f = open(WEBCAMIMAGE, 'rb')
        bot.sendPhoto(ADMINCHATID, f)
    else:
        bot.sendMessage(chat_id, errorMsg)

    flavor = telepot.flavor(msg)

    summary = telepot.glance(msg, flavor=flavor)
    print flavor, summary

bot = telepot.Bot(config.get('Telegram','token', 0))
bot.message_loop(handle)
print 'Listening ...'

# Keep the program running.
while 1:
    try:
        time.sleep(10)
        if prov.lastOpenWeatherCheck == None:
            prov.queryOpenWeather()
            prov.sendOpenWeather()
            prov.sendWetterArchiv()
        if datetime.datetime.now() > prov.lastOpenWeatherCheck + datetime.timedelta(minutes=int(config.get('OpenWeatherMap', 'interval'))):
            prov.queryOpenWeather()
            prov.sendOpenWeather()
            prov.sendWetterArchiv()

        if datetime.datetime.now() > prov.lastCheck + datetime.timedelta(minutes=int(config.get('rasswareBot', 'frostcheckinterval'))):
            prov.lastCheck = datetime.datetime.now()
            for registered in prov.getRegistered():
                chat_id = registered[0]
                sensor_id = registered[1]
                last_alert = registered[2]
	        if prov.checkForFrost(sensor_id) == True and (last_alert == None or datetime.datetime.now() > last_alert + datetime.timedelta(minutes=int(config.get('rasswareBot', 'frostalertdelay')))): 
                    prov.updateLastAlert(chat_id, sensor_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    bot.sendMessage(chat_id, "FROSTWARNUNG!!!111elf\n{}".format("\n".join(prov.getLastTemperatures())))
    except Exception as e:
        print e.__doc__
        print e.message
db.close()
