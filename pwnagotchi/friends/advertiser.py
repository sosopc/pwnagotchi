import _thread
import json
from time import sleep
from .parser import validate, IDWhisperCompression, IDWhisperIdentity,
                    IDWhisperPayload, IDWhisperSignature, IDWhisperStreamHeader,
                    unpack


class FriendsAdvertiser:
    def __init__(self, config, view, keypair):
        self._config = config
        self._view = view
        self._keypair = keypair
        self._peers = {}

    def _on_paket(self, pkt):
        if not pkt.has_layer(Dot11Elt):
            return

        if not validate(pkt):
            return

        payload = unpack(pkt)
        data = json.loads(payload.decode('utf-8'))
        print("FOUND PEER:", data)


    def start_peer_advertiser(self):
        _thread.start_new_thread(self.advertiser, ())

    def start_peer_listener(self):
        _thread.start_new_thread(self.listener, ())

    def advertister(self):
        while True:
            data = {
                'session': {
                    'duration': 'DUMMY',
                    'epochs': 'DUMMY',
                    'train_epochs': 'DUMMY',
                    'avg_reward': 'DUMMY',
                    'min_reward': 'DUMMY',
                    'max_reward': 'DUMMY',
                    'deauthed': 'DUMMY',
                    'associated': 'DUMMY',
                    'handshakes': 'DUMMY',
                    'peers': 'DUMMY',
                },
                'uname': 'DUMMY',
                'brain': 'DUMMY',
                'version': 'DUMMY',
            }
            payload = json.dumps(data, default=str)
            sendp(frames, iface=self._config['main']['iface'])
            sleep(1)

    def listener(self):
        from scapy.all import sniff
        sniff(iface=self._config['main']['iface'], prn=self._on_paket)

