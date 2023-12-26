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

### Install SQLite database

```bash
sudo apt-get install sqlite3
```

### Checkout rasswareBot

```bash
git clone https://github.com/rassware/rasswareBot.git
```

### Database initialization

Run init.sql for creating the database

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

### Get an API key from plot.ly (Free service)

https://plot.ly/

Follow the instructions on the page to get an API key

### Update config file

Replace the placeholder with your values.

### Create a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

### Start your bot

python rasswareBot.py

All done! Have fun with your new weather bot!
