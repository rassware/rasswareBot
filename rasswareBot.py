# -*- coding: utf-8 -*-

import sys
import time
import datetime
import MySQLdb
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

class DataProvider:

    tempField = "temperature_C_dec"
    humiField = "humidity_dec"
    lastCheck = datetime.datetime.now()
    lastOpenWeatherCheck = None

    def __init__(self, db):
        self.db = db

    def getLastValues(self,field):
        sql = """select s.model, s.sensor_id, s.time, s.{0}
                 from sensors s
                 join (select max(id) as id from sensors where {0} is not null and sensor_id > 0 group by sensor_id) as d on s.id = d.id
                 order by s.model,s.sensor_id""".format(field)
        cur = self.db.cursor()
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
        cur.close()
        return data

    def getLastNightTemperatures(self):
        sql = """select model, sensor_id, min(temperature_C_dec), max(temperature_C_dec) from sensors where 
                 time between subdate(concat(cast(date(current_timestamp()) as char),' 06:00:00.0'), interval 12 hour) and concat(cast(date(current_timestamp()) as char),' 06:00:00.0') and
                 temperature_C_dec is not null and sensor_id > 0
                 group by model, sensor_id"""
        cur = self.db.cursor()
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
        cur.close()
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
        cur = self.db.cursor()
        cur.execute("INSERT IGNORE INTO registered(chatid, sensor_id) VALUES ({0}, {1});".format(chatId, sensor_id))
        db.commit()
        cur.close()

    def unregisterForAlert(self, chatId, sensor_id):
        cur = self.db.cursor()
        cur.execute("DELETE FROM registered WHERE chatid = {0} and sensor_id = {1};".format(chatId, sensor_id))
        db.commit()
        cur.close()

    def updateLastAlert(self, chatId, sensor_id, last_alert):
        cur = self.db.cursor()
        cur.execute("UPDATE registered SET last_alert = '{0}' WHERE chatid = {1} and sensor_id = {2};".format(last_alert, chatId, sensor_id))
        db.commit()
        cur.close()

    def getRegistered(self):
        cur = self.db.cursor()
        cur.execute("SELECT chatid, sensor_id, last_alert FROM registered;")
        data = []
        for row in cur.fetchall():
            last_alert = datetime.datetime.strptime(str(row[2]), DATEFORMAT) if row[2] != None else None
            data.append([int(row[0]), row[1], last_alert])
        cur.close()
        return data

    def getWeatherInfo(self):
        cur = self.db.cursor()
        cur.execute("SELECT description,pressure,wind_speed,wind_deg,sunrise,sunset,date_created FROM open_weather ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        description = row[0].encode('utf-8')
        pressure = float(row[1])
        wind_speed = float(row[2])
        wind_deg = float(row[3])
        sunrise = datetime.datetime.strptime(str(row[4]), DATEFORMAT).strftime('%H:%M:%S')
        sunset = datetime.datetime.strptime(str(row[5]), DATEFORMAT).strftime('%H:%M:%S')
        date_created = str(row[6])
        return "Wetterdaten von {0}\n{1}\nLuftdruck: {2} hPa\nWindstärke: {3} m/s\nWindrichtung: {4}°\nSonnenaufgang: {5}\nSonnenuntergang: {6}".format(date_created,description,pressure,wind_speed,wind_deg,sunrise,sunset)

    def queryOpenWeather(self):
        url = "http://api.openweathermap.org/data/2.5/weather?zip={}&lang=de&units=metric&APPID={}".format(config.get('OpenWeatherMap', 'zip', 1), config.get('OpenWeatherMap', 'key', 1))
        response = requests.post(url)
        print "Query OpenWeather API ..."
        try:
            data = json.loads(response.text)
            cur = self.db.cursor()
            cur.execute("INSERT INTO open_weather(description,pressure,wind_speed,wind_deg,sunrise,sunset) VALUES ('{0}',{1},{2},{3},FROM_UNIXTIME({4}),FROM_UNIXTIME({5}))".format(data['weather'][0]['description'].encode('utf8'), data['main']['pressure'], data['wind']['speed'], data['wind']['deg'], data['sys']['sunrise'], data['sys']['sunset']))
            db.commit()
            cur.close()
        except ValueError:
            print "Could not query OpenWeater API"
        self.lastOpenWeatherCheck = datetime.datetime.now()

    def sendOpenWeather(self):
        cur = self.db.cursor()
        cur.execute("SELECT temperature_C_dec FROM sensors WHERE sensor_id = '3' AND temperature_C_dec IS NOT NULL ORDER BY ID DESC LIMIT 1")
        row = cur.fetchone()
        temp = row[0]
        cur.execute("SELECT humidity_dec FROM sensors WHERE sensor_id = '3' AND humidity_dec IS NOT NULL ORDER BY ID DESC LIMIT 1")
        row = cur.fetchone()
        humi = row[0]
        cur.close()
        lat = config.get('OpenWeatherMap', 'lat')
        lng = config.get('OpenWeatherMap', 'lng')
        alt = config.get('OpenWeatherMap', 'alt')
        name = config.get('OpenWeatherMap', 'name', 1)
        user = config.get('OpenWeatherMap', 'user', 1)
        pw = config.get('OpenWeatherMap', 'pw', 1)
        data = {'temp': temp, 'humidity': humi, 'lat': lat, 'long': lng, 'alt': alt, 'name': name}
        response = requests.post('http://openweathermap.org/data/post', data, auth=(user, pw))
        print "send data to OpenWeather API: " + response.text

    def getPressureHistory(self, limit):
        cur = self.db.cursor()
        cur.execute("SELECT date_created,pressure FROM open_weather ORDER BY id DESC LIMIT {0}".format(limit))
        data = cur.fetchall()
        cur.close
        return data

db = MySQLdb.connect(host=config.get('Database', 'host', 1), user=config.get('Database', 'user', 1), passwd=config.get('Database', 'pw', 1), db=config.get('Database', 'db', 1), charset="utf8") 
db.autocommit(True) 
prov = DataProvider(db)
errorMsg = "Das habe ich nicht verstanden ..."
helpMsg = """
/lastTemp - Liefert aktuelle Temperaturwerte
/lastHumi - Liefert aktuelle Luftfeuchtigkeitswerte
/lastNightTemp - Liefert die MIN/MAX Temperaturen der letzten Nacht
/pressure <limit> - Liefert historische Luftdruckwerte
/graph <limit> - Zeichnet ein Luftdruckdiagramm
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
        args = command.split(' ',1)
        limit = int(args[-1]) if args[-1].isdigit() else 10
        if len(args) > 2 or limit > 100:
            bot.sendMessage(chat_id, "Syntax: \"/pressuregraph <limit>\"\nLimit max 100")
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
    elif command == "/help":
        bot.sendMessage(chat_id, helpMsg)
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
    time.sleep(10)
    if prov.lastOpenWeatherCheck == None:
        prov.queryOpenWeather()
#        prov.sendOpenWeather()
    if datetime.datetime.now() > prov.lastOpenWeatherCheck + datetime.timedelta(minutes=int(config.get('OpenWeatherMap', 'interval'))):
        prov.queryOpenWeather()
#        prov.sendOpenWeather()

    if datetime.datetime.now() > prov.lastCheck + datetime.timedelta(minutes=int(config.get('rasswareBot', 'frostcheckinterval'))):
        prov.lastCheck = datetime.datetime.now()
        for registered in prov.getRegistered():
            chat_id = registered[0]
            sensor_id = registered[1]
            last_alert = registered[2]
	    if prov.checkForFrost(sensor_id) == True and (last_alert == None or datetime.datetime.now() > last_alert + datetime.timedelta(minutes=int(config.get('rasswareBot', 'frostalertdelay')))): 
                prov.updateLastAlert(chat_id, sensor_id, datetime.datetime.now())
                bot.sendMessage(chat_id, "FROSTWARNUNG!!!111elf\n{}".format("\n".join(prov.getLastTemperatures())))

db.close()
