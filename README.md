# rasswareBot

A telegram bot for weather infos based on a DVB-T USB dongle with the RealtekRTL2832U chip, a Raspberry Pi V2 and the software rtl_433.

### Compile rtl_433 on your RaspberryPi

```bash
git clone https://github.com/merbanan/rtl_433
cd rtl_433/
autoreconf -i
./configure
make
make install
```

### Install MySQL database

```bash
sudo apt-get install mysql-server
```

### Checkout rasswareBot

```bash
git clone https://github.com/rassware/rasswareBot.git
```

### Database initialization

Run init.sql for creating the database (change password for user!)

### Install Telegram/Python framwork 'telepot'

```bash
git clone https://github.com/nickoala/telepot.git
cd telepot/
sudo python setup.py install
```

### Add the bash script to a crontab

```bash
*/15 * * * * <path to your script>/querySensors.sh > /dev/null 2>&1
```

### Add your bot to the BotFather in Telegram

https://core.telegram.org/bots#3-how-do-i-create-a-bot

### Get an API key from OpenWeather (Free service is OK)

http://openweathermap.org/

### Start your bot

python rasswareBot.py \<Telegram Token from Botfather\> \<OpenWeatherAPI key\> \<postalcode\>,\<ISO country code\>

All done! Have fun with your new weather bot!
