#!/bin/bash

# script to get clima data into the sqlite db

#kill existing processes
pkill rtl_433
pkill rtlclient

#run 2 mins for data
timeout 120 scripts/raspi/rtlclient.sh -f 433920000 -a 192.168.78.28 -p 1234 -s 250000 | rtl_433 -F csv -G -U -r /dev/stdin > /tmp/sensors.csv
#/usr/local/bin/rtl_433 -F csv -T 120 -p -32 > /tmp/sensors.csv

# import file to database
echo -e "DROP TABLE IF EXISTS import_sensors;" | sqlite3 /home/crassmann/databases/climadb.db
echo -e ".separator ","\n.import /tmp/sensors.csv import_sensors" | sqlite3 /home/crassmann/databases/climadb.db

# delete csv
rm /tmp/sensors.csv

# do some transformations
echo -e "INSERT INTO sensors('time','model','sensor_id','channel','battery','temperature_C','temperature_C_dec','crc','rid','button','humidity','humidity_dec','state','rain_rate','rain_total','unit','group_call','command','dim','dim_value','wind_speed','wind_gust','wind_direction','device','temperature_F','direction_str','direction_deg','speed','gust','rain','msg_type','hours','minutes','seconds','year','month','day','ws_id','rainfall_mm','wind_speed_ms','gust_speed_ms','rc','flags','maybetemp','binding_countdown','depth','power0','power1','power2','node','ct1','ct2','ct3','ct4','Vrms_batt','temp1_C','temp2_C','temp3_C','temp4_C','temp5_C','temp6_C','pulse','sid','transmit','moisture','status','type','make','pressure_PSI','battery_mV','checksum','pressure','code','power','device_id','len','s_to','s_from','payload') SELECT DATETIME('now','localtime'),model,id,channel,battery,temperature_C,CASE WHEN temperature_C != '' THEN CAST(temperature_C as REAL) ELSE NULL END,'',rid,button,humidity,CASE WHEN humidity != '' THEN CAST(humidity as REAL) ELSE NULL END,state,rain_rate,rain_total,unit,group_call,command,dim,dim_value,wind_speed,wind_gust,wind_direction,device,temperature_F,direction_str,direction_deg,speed,gust,rain,msg_type,hours,minutes,seconds,year,month,day,ws_id,rainfall_mm,wind_speed_ms,gust_speed_ms,rc,flags,maybetemp,binding_countdown,depth,power0,power1,power2,node,ct1,ct2,ct3,ct4,\"Vrms/batt\",temp1_C,temp2_C,temp3_C,temp4_C,temp5_C,temp6_C,pulse,sid,transmit,moisture,status,type,'',pressure_PSI,battery_mV,'','',code,'',\"device id\",len,\"to\",\"from\",payload FROM import_sensors;" | sqlite3 /home/crassmann/databases/climadb.db
