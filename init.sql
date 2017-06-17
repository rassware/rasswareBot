CREATE TABLE sensors (
id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
time DATETIME,
model VARCHAR(250),
sensor_id VARCHAR(10),
channel VARCHAR(10),
battery VARCHAR(10),
temperature_C VARCHAR(10),
temperature_C_dec DECIMAL(7,3) NULL,
crc VARCHAR(10),
rid VARCHAR(10),
button VARCHAR(10),
humidity VARCHAR(10),
humidity_dec DECIMAL(7,3) NULL,
state VARCHAR(10),
rain_rate VARCHAR(10),
rain_total VARCHAR(10),
unit VARCHAR(10),
group_call VARCHAR(10),
command VARCHAR(10),
dim VARCHAR(10),
dim_value VARCHAR(10),
wind_speed VARCHAR(10),
wind_gust VARCHAR(10),
wind_direction VARCHAR(10),
device VARCHAR(10),
temperature_F VARCHAR(10),
direction_str VARCHAR(10),
direction_deg VARCHAR(10),
speed VARCHAR(10),
gust VARCHAR(10),
rain VARCHAR(10),
msg_type VARCHAR(10),
hours VARCHAR(3),
minutes VARCHAR(3),
seconds VARCHAR(3),
year VARCHAR(3),
month VARCHAR(3),
day VARCHAR(3),
ws_id VARCHAR(3),
rainfall_mm VARCHAR(10),
wind_speed_ms VARCHAR(10),
gust_speed_ms VARCHAR(10),
rc VARCHAR(10),
flags VARCHAR(10),
maybetemp VARCHAR(10),
binding_countdown VARCHAR(10),
depth VARCHAR(10),
power0 VARCHAR(10),
power1 VARCHAR(10),
power2 VARCHAR(10),
node VARCHAR(10),
ct1 VARCHAR(10),
ct2 VARCHAR(10),
ct3 VARCHAR(10),
ct4 VARCHAR(10),
Vrms_batt VARCHAR(10),
temp1_C VARCHAR(10),
temp2_C VARCHAR(10),
temp3_C VARCHAR(10),
temp4_C VARCHAR(10),
temp5_C VARCHAR(10),
temp6_C VARCHAR(10),
pulse VARCHAR(10),
sid VARCHAR(10),
transmit VARCHAR(10),
moisture VARCHAR(10),
status VARCHAR(10),
type VARCHAR(10),
make VARCHAR(10),
pressure_PSI VARCHAR(10),
battery_mV VARCHAR(10),
checksum VARCHAR(10),
pressure VARCHAR(10),
code VARCHAR(10),
power VARCHAR(10),
device_id VARCHAR(10),
len VARCHAR(10),
s_to VARCHAR(10),
s_from VARCHAR(10),
payload VARCHAR(10),
date_created TIMESTAMP DEFAULT NOW()
);

CREATE TABLE registered(
id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
chatid BIGINT NOT NULL,
sensor_id VARCHAR(10) NOT NULL,
last_alert DATETIME NULL,
date_created TIMESTAMP DEFAULT NOW(),
UNIQUE KEY `idx_chatid` (chatid, sensor_id)
);

CREATE TABLE open_weather(
id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
description VARCHAR(250),
pressure DECIMAL(10,4),
wind_speed DECIMAL(10,4),
wind_deg DECIMAL(10,4),
sunrise DATETIME,
sunset DATETIME,
date_created TIMESTAMP DEFAULT NOW()
);

CREATE INDEX model_idx ON sensors ( sensor_id,model );
CREATE INDEX date_created_idx ON sensors ( date_created );
CREATE INDEX "idx_sensor_id" ON "sensors" (sensor_id);
CREATE INDEX "idx_sensors_time" ON "sensors" (time);
CREATE INDEX "idx_sensor_id_time" ON "sensors" (sensor_id,time);

