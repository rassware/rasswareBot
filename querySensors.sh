#!/bin/bash

#run 5 mins for data
rtl_433 -F csv -T 120 > /tmp/sensors.csv

# import file to database
mysqlimport -uclimabot -pStart#123 --lines-terminated-by="\n" --fields-terminated-by="," --ignore-lines=1 --local --columns=time,model,sensor_id,channel,battery,temperature_C,crc,rid,button,humidity,state,rain_rate,rain_total,unit,group_call,command,dim,dim_value,wind_speed,wind_gust,wind_direction,device,temperature_F,direction_str,direction_deg,speed,gust,rain,msg_type,hours,minutes,seconds,year,month,day,ws_id,rainfall_mm,wind_speed_ms,gust_speed_ms,rc,flags,maybetemp,binding_countdown,depth,power0,power1,power2,node,ct1,ct2,ct3,ct4,Vrms_batt,temp1_C,temp2_C,temp3_C,temp4_C,temp5_C,temp6_C,pulse,sid,transmit,moisture,status,type,make,pressure_PSI,battery_mV,checksum,pressure,code,power,device_id,len,s_to,s_from,payload climadb /tmp/sensors.csv

# delete csv
rm /tmp/sensors.csv

# do some transformations
mysql -uclimabot -pStart#123 -D climadb -e'UPDATE sensors SET temperature_C_dec = temperature_C WHERE temperature_C <> "" AND temperature_C_dec IS NULL;'
mysql -uclimabot -pStart#123 -D climadb -e'UPDATE sensors SET humidity_dec = humidity WHERE humidity <> "" AND humidity_dec IS NULL;'
