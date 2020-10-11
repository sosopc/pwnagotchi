import zlib
from .utils import chunked_iterable, compress, decompress


IDWhisperPayload       = 222
IDWhisperCompression   = 223
IDWhisperIdentity      = 224
IDWhisperSignature     = 225
IDWhisperStreamHeader  = 226


def validate(pkt):
    return hasattr(pkt, 'ID') and int(pkt.ID) in [IDWhisperStreamHeader,
                                                  IDWhisperSignature,
                                                  IDWhisperCompression,
                                                  IDWhisperIdentity,
                                                  IDWhisperPayload]


def pack(from_addr, payload):
    dot11 = Dot11(type=0,
                  addr1='ff:ff:ff:ff:ff:ff',
                  addr2='de:ad:be:ef:de:ad',
                  addr3=from_addr)

    beacon = Dot11Beacon(cap='ESS+privacy')

    pkt = RadioTap()/dot11/beacon

    compressed = bytearray(compress(payload))

    if len(compressed) < len(payload):
        payload = compressed
        pkt = pkt/Dot11Elt(ID=IDWhisperCompression)

    for d in chunked_iterable(payload, 0xff):
        pkt = pkt/Dot11Elt(ID=IDWhisperPayload, info=d)

    return pkt


def unpack(pkt):
    compressed = False
    payload = bytearray()

    for layer in pkt:
        if layer.ID == IDWhisperPayload:
            payload.extend(layer.info)
        elif layer.ID == IDWhisperCompression:
            compressed = True

    if not compressed:
        return payload

    return decompress(payload)
