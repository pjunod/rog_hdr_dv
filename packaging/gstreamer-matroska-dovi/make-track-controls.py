#!/usr/bin/python3
"""Generate private track-header controls without changing coded picture bytes."""
from pathlib import Path
import argparse
import hashlib
import json


def vint(data, offset, identity=False):
    first = data[offset]
    width = next((i for i in range(1, 9) if first & (1 << (8-i))), None)
    if width is None or offset + width > len(data) or (identity and width > 4):
        raise ValueError('invalid EBML variable integer')
    value = int.from_bytes(data[offset:offset+width], 'big')
    if not identity:
        value &= (1 << (7*width))-1
    return value, width, not identity and value == (1 << (7*width))-1


def elements(data):
    offset = 0
    while offset < len(data):
        identity, ni, _ = vint(data, offset, True)
        size, ns, unknown = vint(data, offset+ni)
        start = offset+ni+ns
        end = len(data) if unknown else start+size
        if end > len(data):
            raise ValueError('element exceeds containing master')
        yield identity, data[start:end]
        offset = end


def element(identity, payload):
    ib = identity.to_bytes((identity.bit_length()+7)//8, 'big')
    n = next(n for n in range(1, 9) if len(payload) < (1 << (7*n))-1)
    return ib + ((1 << (7*n)) | len(payload)).to_bytes(n, 'big') + payload


def mapping(type_value, payload, order='type-first', duplicate=None):
    kind = element(0x41e7, type_value.to_bytes(4, 'big'))
    extra = element(0x41ed, payload)
    parts = [kind, extra] if order == 'type-first' else [extra, kind]
    if duplicate == 'type':
        parts.append(kind)
    if duplicate == 'extra':
        parts.append(extra)
    return element(0x41e4, b''.join(parts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    data = args.input.read_bytes()
    if len(data) > 64*1024*1024:
        raise ValueError('bounded control input exceeds 64MiB')
    top = list(elements(data))
    header = next(p for i,p in top if i == 0x1a45dfa3)
    segment = list(elements(next(p for i,p in top if i == 0x18538067)))
    tracks = list(elements(next(p for i,p in segment if i == 0x1654ae6b)))
    originals = [list(elements(p)) for i,p in tracks if i == 0xae]
    assert len(originals) == 1, 'controls require one original track'
    original = originals[0]
    config = None
    for identity,payload in original:
        if identity == 0x41e4:
            children = dict(elements(payload))
            if int.from_bytes(children.get(0x41e7,b''),'big') == 0x64766343:
                assert config is None, 'ambiguous input'
                config = children[0x41ed]
    assert config is not None and len(config) == 24
    assert config[0:2] == b'\x01\x00' and config[2] >> 1 == 5
    plain = [(i,p) for i,p in original if i != 0x41e4]
    info = [(i,p) for i,p in segment if i == 0x1549a966]
    cluster = next((i,p) for i,p in segment if i == 0x1f43b675)
    args.output.mkdir()
    cases = []

    def write(name, declarations, expected, second=None, codec=None, before=False):
        entry = [(i, codec if codec is not None and i == 0x86 else p)
                 for i,p in plain]
        encoded = b''.join(element(i,p) for i,p in entry)
        additions = b''.join(declarations)
        encoded = additions+encoded if before else encoded+additions
        encoded_tracks = element(0xae, encoded)
        expectations = ['video_0:'+('-' if expected is None else expected.hex())]
        if second is not None:
            # A second independently numbered track gets the original codec
            # parameters but never implicitly inherits track one's declaration.
            second_entry = b''.join(element(i,b'\x02' if i in (0xd7,0x73c5)
                                              else p) for i,p in plain)
            encoded_tracks += element(0xae, second_entry + b''.join(second[0]))
            expectations.append('video_1:'+('-' if second[1] is None else second[1].hex()))
        # Drop seek/cue offsets rather than retaining invalid positions after
        # header-size changes. Coded Cluster bytes remain exactly unchanged.
        body = b''.join(element(i,p) for i,p in info)
        body += element(0x1654ae6b, encoded_tracks) + element(*cluster)
        path = args.output/(name+'.mkv')
        path.write_bytes(element(0x1a45dfa3,header)+element(0x18538067,body))
        cases.append({'name':name,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'expected':expectations})

    valid = mapping(0x64766343, config)
    write('plain', [], None)
    write('type-first', [valid], config)
    write('data-first', [mapping(0x64766343,config,'data-first')], config)
    write('mapping-before-codec', [valid], config, before=True)
    write('duplicate-mapping', [valid,valid], None)
    write('duplicate-type', [mapping(0x64766343,config,duplicate='type')], None)
    write('duplicate-extra', [mapping(0x64766343,config,duplicate='extra')], None)
    write('missing-extra', [element(0x41e4,element(0x41e7,b'dvcC'))],None)
    write('missing-type', [element(0x41e4,element(0x41ed,config))],None)
    write('invalid-type-width', [element(0x41e4,element(0x41e7,b'\0'*5+b'dvcC')+element(0x41ed,config))],None)
    profile8=bytearray(config)
    fields=int.from_bytes(config[2:4],'big')
    profile8[2:4]=((8<<9)|(fields&0x1ff)).to_bytes(2,'big')
    profile8[4]=0x10
    write('conflicting-mappings',[valid,mapping(0x64767643,bytes(profile8))],None)
    for name,payload in [('empty',b''),('short',config[:3]),('oversize',config+b'\0'),('large',b'\0'*(1024*1024)),('bad-version',b'\x02'+config[1:]),('bad-reserved',config[:-1]+b'\x01')]:
        write(name,[mapping(0x64766343,payload)],None)
    write('abbreviated-four',[mapping(0x64766343,config[:4])],config[:4])
    write('abbreviated-twentythree',[mapping(0x64766343,config[:23])],config[:23])
    write('profile-type-mismatch',[mapping(0x64767643,config)],None)
    unknown=mapping(0x12345678,config)
    write('unknown-type',[unknown],None)
    write('unknown-plus-valid',[unknown,valid],config)
    write('track-isolation-valid-plain',[valid],config,second=([],None))
    write('track-isolation-bad-valid',[mapping(0x64766343,b'\0')],None,second=([valid],config))
    write('non-hevc',[valid],None,codec=b'V_VP9')
    receipt={'input_sha256':hashlib.sha256(data).hexdigest(),'config_sha256':hashlib.sha256(config).hexdigest(),'cluster_sha256':hashlib.sha256(cluster[1]).hexdigest(),'scope':'Track configuration transport only; controls retain one original Cluster byte-exact; no FEL reconstruction claim','cases':cases}
    (args.output/'manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'cases':len(cases),'input_sha256':receipt['input_sha256']},indent=2))

if __name__ == '__main__':
    main()
