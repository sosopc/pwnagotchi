#!/usr/bin/env bash

# name of the ethernet gadget interface on the host
USB_IFACE="$(find /sys/class/net -name "enp*" -printf "%f\n" | tail -1)"
USB_IFACE_IP=10.0.0.1
USB_IFACE_NET=10.0.0.0/24
# host interface to use for upstream connection
UPSTREAM_IFACE=$(ip r g 8.8.8.8 | head -n1 | cut -d" " -f5)

ip addr add "$USB_IFACE_IP/24" dev "$USB_IFACE"
ip link set "$USB_IFACE" up

iptables -A FORWARD -o "$UPSTREAM_IFACE" -i "$USB_IFACE" -s "$USB_IFACE_NET" -m conntrack --ctstate NEW -j ACCEPT
iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -t nat -F POSTROUTING
iptables -t nat -A POSTROUTING -o "$UPSTREAM_IFACE" -j MASQUERADE

echo 1 > /proc/sys/net/ipv4/ip_forward
