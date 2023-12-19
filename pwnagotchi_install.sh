#!/usr/bin/env bash

# install pwnagotchi on rpi4

WIFI_DEV="wlan1"
AUTO_MODE=true
DEBUG=false
PWN_GRID=false
PWN_GRID_REPORT=false
HOME_NETWORK="YourHomeNetworkMaybe"
DISPLAY_TYPE="waveshare_2"
DISPLAY_ENABLED=false
PWN_BLUETOOTH_IP=192.168.44.44
PHONE_BLUETOOTH_MAC=FF:FF:FF:FF:FF
BETTERCAP_PKG="bettercap_linux_armhf_v2.26.1.zip"
PWDGRID_PKG="pwngrid_linux_armhf_v1.10.3.zip"

# raspbian buster lite dependencies
cat > /tmp/dependencies << EOF
rsync
vim
screen
golang
git
build-essential
python3-pip
python3-mpi4py
python3-smbus
unzip
gawk
libopenmpi-dev
libatlas-base-dev
libjasper-dev
libqtgui4
libqt4-test
libopenjp2-7
libtiff5
tcpdump
lsof
libilmbase23
libopenexr23
libgstreamer1.0-0
libavcodec58
libavformat58
libswscale5
libpcap-dev
libusb-1.0-0-dev
libnetfilter-queue-dev
libopenmpi3
dphys-swapfile
kalipi-kernel
kalipi-bootloader
kalipi-re4son-firmware
kalipi-kernel-headers
libraspberrypi0
libraspberrypi-dev
libraspberrypi-doc
libraspberrypi-bin
fonts-dejavu
fonts-dejavu-core
fonts-dejavu-extra
python3-pil
python3-smbus
libfuse-dev
bc
fonts-freefont-ttf
fbi
python3-flask
python3-flask-cors
python3-flaskext.wtf
EOF

sudo apt -q update
for pkg in $(cat /tmp/dependencies)
do
  sudo apt install -y $pkg
done

# 1. bettercap
wget "https://github.com/bettercap/bettercap/releases/download/v2.26.1/$BETTERCAP_PKG"
unzip $BETTERCAP_PKG
DOWNLOAD_SHA256_DIGEST="$(cat bettercap_linux_armhf_v2.26.1.sha256 | awk '{print $2}')"
CALCULATED_SHA256="$(sha256sum bettercap | cut -d " " -f1)"
if [ "$DOWNLOAD_SHA256_DIGEST" != "$CALCULATED_SHA256" ];
then
    echo "SHA256_DIGEST does not match"
    exit 1
fi

## ... check the sha256 digest before doing this ...
sudo mv bettercap /usr/bin/

## install the caplets and the web ui in /usr/local/share/bettercap and quit
sudo bettercap -eval "caplets.update; ui.update; quit" || exit

## create system services
sudo bash -c 'cat > /usr/bin/bettercap-launcher' << EOF
#!/usr/bin/env bash
/usr/bin/monstart
if [[ \$(ifconfig | grep usb0 | grep RUNNING) ]] || [[ \$(cat /sys/class/net/eth0/carrier) ]]; then
  # if override file exists, go into auto mode
  if [ -f /root/.pwnagotchi-auto ]; then
    /usr/bin/bettercap -no-colors -caplet pwnagotchi-auto -iface $WIFI_DEV
  else
    /usr/bin/bettercap -no-colors -caplet pwnagotchi-manual -iface $WIFI_DEV
  fi
else
  /usr/bin/bettercap -no-colors -caplet pwnagotchi-auto -iface $WIFI_DEV
fi
EOF

sudo chmod u+x /usr/bin/bettercap-launcher

sudo bash -c 'cat > /etc/systemd/system/bettercap.service' << EOF
[Unit]
Description=bettercap api.rest service.
Documentation=https://bettercap.org
Wants=network.target
#After=pwngrid.service

[Service]
Type=simple
PermissionsStartOnly=true
ExecStart=/usr/bin/bettercap-launcher
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable bettercap.service

# 2. pwngrid

# method to create pwngrid-peer.service
create_pwngrid_service(){
sudo bash -c 'cat > /etc/systemd/system/pwngrid-peer.service' << EOF
[Unit]
Description=pwngrid peer service.
Documentation=https://pwnagotchi.ai
Wants=network.target

[Service]
Type=simple
PermissionsStartOnly=true
ExecStart=/usr/bin/pwngrid -keys /etc/pwnagotchi -address 127.0.0.1:8666 -client-token /root/.api-enrollment.json -wait -log /var/log/pwngrid-peer.log -iface $WIFI_DEV
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
}

## download and uncompress code
wget "https://github.com/evilsocket/pwngrid/releases/download/v1.10.3/$PWDGRID_PKG"
unzip $PWDGRID_PKG

## ... check the sha256 digest before doing this ...
sudo mv pwngrid /usr/bin/

## generate the keypair
sudo pwngrid -generate -keys /etc/pwnagotchi

## create system service
create_pwngrid_service

if ! $PWN_GRID
then
    sudo systemctl stop pwngrid-peer.service
    sudo systemctl disable pwngrid-peer.service
    ## disable dependency in bettercap service launch script
    sudo bash -c "sed -i 's/^After=pwngrid.service/#After=pwngrid.service/g' /etc/systemd/system/bettercap.service"
else
    sudo systemctl enable pwngrid-peer.service
fi

# 3. pwnagotchi

## download and uncompress code
wget "https://github.com/evilsocket/pwnagotchi/archive/v1.4.3.zip"
unzip v1.4.3.zip
cd pwnagotchi-1.4.3 || exit

## this will install the requirements and pwnagotchi itself
echo "werkzeug==0.16.1" >> requirements.txt
echo "imutils==0.5.3" >> requirements.txt
echo "opencv-python==3.4.6.27" >> requirements.txt

sudo pip3 install -r requirements.txt
sudo pip3 install .

# install the default configuration
echo "previous step installs default configuration file in /etc/pwnagotchi/default.yml,"
echo "in order to apply customizations you’ll need to create a new /etc/pwnagotchi/config.yml file"
echo "https://pwnagotchi.ai/configuration/"

sudo mkdir -p /etc/pwnagotchi/
sudo bash -c 'cat > /etc/pwnagotchi/config.yml' << EOF
  main:
    name: 'pwnagotchi'
    whitelist:
      - $HOME_NETWORK
    plugins:
      grid:
        enabled: $PWN_GRID
        report: $PWN_GRID_REPORT
        exclude:
          - $HOME_NETWORK
      bt-tether:
        enabled: true
        devices:
          my-phone1:                    # you can choose your phones name here
            enabled: true               # enables the device
            search_order: 1             # in which order the devices should be searched. E.g. this is #1.
            mac: $PHONE_BLUETOOTH_MAC   # you need to put your phones bt-mac here (the same as above,
                                        ## or goto your phones   settings > status)
            ip: $PWN_BLUETOOTH_IP       # this is the static ip of your pwnagotchi
                                        ## adjust this to your phones pan-network (run "ifconfig bt-pan" on your phone)
                                        ## if you feel lucky, try: 192.168.44.44 (Android) or 172.20.10.6 (iOS)
                                        ## 44 is just an example, you can choose between 2-254 (if netmask is 24)
            netmask: 24                 # netmask of the PAN
            interval: 1                 # in minues, how often should the device be searched
            scantime: 15                # in seconds, how long should be searched on each interval
            share_internet: true        # this will change the routing and nameserver on your pi
            priority: 99                # if you have multiple devices which can share internet; the highest priority wins
            max_tries: 0                # how often should be tried to find the device until it is disabled (to save power)
                                        ## 0 means infinity
          macbook:
            enabled: false

  ui:
      display:
        enabled: $DISPLAY_ENABLED
        type: $DISPLAY_TYPE
        color: 'black'
EOF

sudo chmod u+x /usr/bin/monstart
sudo chmod u+x /usr/bin/pwnagotchi-launcher

## set wifi device
sudo sed -i "s/mon0/$WIFI_DEV/g" /usr/local/share/bettercap/caplets/pwnagotchi-auto.cap
sudo sed -i "s/mon0/$WIFI_DEV/g" /usr/local/share/bettercap/caplets/pwnagotchi-manual.cap
sudo sed -i "s/mon0/$WIFI_DEV/g" /usr/bin/pwnlib

## alias
echo "alias pwnlog='tail -f -n300 /var/log/pwn* | sed --unbuffered \"s/,[[:digit:]]\{3\}\]//g\" | cut -d \" \" -f 2-'" >> ~/.bashrc
echo "alias pwnver='python3 -c \"import pwnagotchi as p; print(p.version)\"'" >> ~/.bashrc

## now start pwnagotchi by simply:

## AUTO mode
if $AUTO_MODE && ! $DEBUG; then sudo pwnagotchi; fi

# AUTO mode with debug logs
if $AUTO_MODE && $DEBUG; then sudo pwnagotchi --debug; fi

# MANU mode
if ! $AUTO_MODE && ! $DEBUG; then sudo pwnagotchi --manual; fi

# MANU mode with debug logs
if ! $AUTO_MODE && $DEBUG; then sudo pwnagotchi --manual --debug; fi
