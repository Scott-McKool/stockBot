#!/bin/sh

# check for root (user id of 0)
 [ `id -u` -ne 0 ] && echo "this script should be run as root" && exit 1

# get discord token from user
echo "get the bot's token from the discord dev portal and enter it here: "
read DISCORDTOKEN 
# get API token from user
echo "get a free token from https://www.alphavantage.co/support/#api-key and then paste it here: "
read APITOKEN 

# make a config file for inportant variables
echo "creating config file 'justinConfig.py'"
    cat > justinConfig.py <<CONFIGFILE
PREFIX = "$"
DISCORD_TOKEN = "$DISCORDTOKEN"
API_TOKEN = "$APITOKEN"
BOT_DIR = "$PWD/"
CONFIGFILE

### install requirements
echo "installing pip with apt. . ."
apt update && apt install python3-pip -y

# install python packages
echo "installing requirements with pip3. . ."
pip3 install -r requirements.txt

### use systemd to run stockbot on system startup
echo "Setting up stockBot.py to run on system startup"
# make a unit file for this systemd service
echo "creating unit file 'stockBot.service'"
    cat > stockBot.service <<UNITFILE
[Unit]
Description=Runs stockBot.py script on startup
After=multi-user.target
[Service]
ExecStart=/usr/bin/python3 "$PWD/stockBot.py"
[Install]
WantedBy=multi-user.target
UNITFILE
# put the unitfile in its place w/ systemd
mv stockBot.service /etc/systemd/system/stockBot.service
# reload systemd so it can find this newly created service
echo "reloding systemctl daemon"
systemctl daemon-reload
# enable this service in systemd
echo "enabling stockBot.service"
systemctl enable stockBot.service

echo "stockBot service has been added and enabled"
echo "stockBot.py will be automatically run on startup from now on"
echo ""
echo "to dissable running on startup type 'sudo systemctl disable stockBot.service'"
echo ""

exit 0