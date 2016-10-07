# -*- coding: utf-8 -*-

import sys
import time
import datetime
import MySQLdb
import telepot

TOKEN = sys.argv[1]      # get token from command-line
MINUTESDELAYALERT = 60*6 # minutes between frost alerts
TEMPFROSTCHECK = 2.0     # trigger temperatur for frost alert

class DataProvider:

    tempField = "temperature_C_dec"
    humiField = "humidity_dec"
    lastAlert = datetime.datetime.now()
    lastCheck = datetime.datetime.now()
    chatIdsForAlert = set()

    def __init__(self, db):
        self.db = db

    def getLastValues(self,field):
        sql = """select s.model, s.sensor_id, s.time, s.{0}
                 from sensors s
                 join (select max(id) as id from sensors where {0} is not null and sensor_id > 0 group by sensor_id) as d on s.id = d.id
                 order by s.time desc""".format(field)
        cur = self.db.cursor()
        a = cur.execute(sql)
        data = []
        if a == 0:
            data.extend("Keine Klimadaten gefunden!")
        else:
            for row in cur.fetchall():
                messzeit = str(row[2])
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
                data.append("{0}[{1}] min: {2}{4} max: {3}{4}".format(sensor, id, minValue, maxValue, " °C"))
        cur.close()
        return data

    def getLastTemperatures(self):
        result = []
        label = " °C"
        data = self.getLastValues(self.tempField)
        for i in data:
            result.append("{0}[{1}] {2}: {3}{4}".format(i[0], i[1], i[2], i[3], label))
        return result

    def getLastHumidities(self):
        result = []
        label = " %"
        data = self.getLastValues(self.humiField)
        for i in data:
            result.append("{0}[{1}] {2}: {3}{4}".format(i[0], i[1], i[2], i[3], label))
        return result 

    def checkForFrost(self):
        print "Frost check at {}".format(self.lastCheck)
        data = self.getLastValues(self.tempField)
        for item in data:
            if item[3] < TEMPFROSTCHECK:
                print "Frost da! {} °C".format(item[3])
                return True
        return False

    def registerForAlert(self, chatId):
        self.chatIdsForAlert.add(chatId)

    def unregisterForAlert(self, chatId):
        self.chatIdsForAlert.remove(chatId)

db = MySQLdb.connect(host="localhost", user="climabot", passwd="Start#123", db="climadb")
prov = DataProvider(db)

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
    elif command == '/checkForFrost':
        if prov.checkForFrost() == False:
            bot.sendMessage(chat_id, "Noch kein Frost da :)")
        else:
            bot.sendMessage(chat_id, "OK, jetzt ist der Frost da! Hoffentlich sind die Pflanzen drin!")
    elif command == "/register":
        prov.registerForAlert(chat_id)
        bot.sendMessage(chat_id, "Erfolgreich registriert!")
    elif command == "/unregister":
        prov.unregisterForAlert(chat_id)
        bot.sendMessage(chat_id, "Erfolgreich abgemeldet!")
    elif command == "/help":
        bot.sendMessage(chat_id, "/lastTemp - Liefert aktuelle Temperaturwerte\n/lastHumi - Liefert aktuelle Luftfeuchtigkeitswerte\n/lastNightTemp - Liefert die MIN/MAX Temperaturen der letzten Nacht\n/checkForFrost - Sagt alles ...\n/register - Für den Frostalarm anmelden\n/unregister - Für den Frostalarm abmelden")
    else:
        bot.sendMessage(chat_id, "Das habe ich nicht verstanden ...")

    flavor = telepot.flavor(msg)

    summary = telepot.glance(msg, flavor=flavor)
    print flavor, summary

bot = telepot.Bot(TOKEN)
bot.message_loop(handle)
print 'Listening ...'

# Keep the program running.
while 1:
    time.sleep(10)
    if datetime.datetime.now() > prov.lastCheck + datetime.timedelta(minutes=5):
        prov.lastCheck = datetime.datetime.now()
	if prov.checkForFrost() == True and datetime.datetime.now() > prov.lastAlert + datetime.timedelta(minutes=MINUTESDELAYALERT): 
            prov.lastAlert = datetime.datetime.now()
            for chat_id in prov.chatIdsForAlert:
                bot.sendMessage(chat_id, "FROSTWARNUNG!!!111elf\n{}".format("\n".join(prov.getLastTemperatures())))

db.close()


