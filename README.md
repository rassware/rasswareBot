# rasswareBot

A telegram bot for weather infos based on a DVB-T USB dongle, a RaspberryPi and the software rtl_433.

1. step: Compile rtl_433 on your RaspberryPi

```bash
git clone https://github.com/merbanan/rtl_433
cd rtl_433/
autoreconf -i
./configure
make
make install
```

2. step: Install MySQL database

```bash
sudo apt-get install mysql-server
```

3. step: Checkout rasswareBot

```bash
git clone https://github.com/rassware/rasswareBot.git
```

4. step: Run init.sql for creating the database (change password for user!)

5. step: Install Telegram/Python framwork 'telepot'

```bash
git clone https://github.com/nickoala/telepot.git
cd telepot/
sudo python setup.py install
```

6. step: Add the bash script to a crontab

```bash
*/15 * * * * <path to your script>/querySensors.sh > /dev/null 2>&1
```

7. step: Add your bot to the BotFather in Telegram

https://core.telegram.org/bots#3-how-do-i-create-a-bot

8. step: Get an API key from OpenWeather (Free service is OK)

http://openweathermap.org/

9. step: Start your bot

python rasswareBot.py <Telegram Token from Botfather> <OpenWeatherAPI key> <postalcode>,<ISO country code>

All done! Have fun with your new weather bot!
