#!/usr/bin/env bash

/root/pwnagotchi/scripts/blink.sh 3 &
test -e /var/tmp/tensorflow-1.13.1-cp37-none-linux_armv6l.whl \
  && pip3 install --no-deps /var/tmp/tensorflow-1.13.1-cp37-none-linux_armv6l.whl \
  && rm /var/tmp/tensorflow-1.13.1-cp37-none-linux_armv6l.whl \
  &&: Goodbye World \
  && sed -i'' '3,8d' "$0"

# blink 10 times to signal ready state
/root/pwnagotchi/scripts/blink.sh 10 &

# start a detached screen session with bettercap
if ifconfig | grep usb0 | grep RUNNING; then
    sudo -H -u root /usr/bin/screen -dmS pwnagotchi -c /root/pwnagotchi/data/screenrc.manual
else
    sudo -H -u root /usr/bin/screen -dmS pwnagotchi -c /root/pwnagotchi/data/screenrc.auto
fi
