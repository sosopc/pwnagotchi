import _thread
from .parser import validate, IDWhisperCompression, IDWhisperIdentity,
                    IDWhisperPayload, IDWhisperSignature, IDWhisperStreamHeader


class FriendsAdvertiser:
    def __init__(self, config, view, keypair):
        self._config = config
        self._view = view
        self._keypair = keypair

    def advertister(self):
        pass

    def _on_paket(self, pkt):
        if not pkt.has_layer(Dot11Elt):
            return

        if not validate(pkt):
            return

        pkt_id = int(pkt.ID)


    def listener(self):
        from scapy.all import sniff
        sniff(iface=self._config['main']['iface'], prn=self._on_paket)

