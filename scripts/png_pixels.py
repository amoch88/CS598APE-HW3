"""Dependency-free decoder for non-interlaced 8-bit RGB PNGs; checks CRCs."""
import struct, zlib, pathlib, hashlib

def decode(path):
    data=pathlib.Path(path).read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n': raise ValueError('bad PNG signature')
    pos=8; compressed=bytearray(); header=None; ended=False
    while pos<len(data):
        length=struct.unpack_from('>I',data,pos)[0]; tag=data[pos+4:pos+8]
        payload=data[pos+8:pos+8+length]
        if len(payload)!=length or pos+12+length>len(data): raise ValueError('truncated chunk')
        crc=struct.unpack_from('>I',data,pos+8+length)[0]
        if zlib.crc32(tag+payload)&0xffffffff != crc: raise ValueError('PNG CRC mismatch')
        if tag==b'IHDR': header=struct.unpack('>IIBBBBB',payload)
        elif tag==b'IDAT': compressed.extend(payload)
        elif tag==b'IEND': ended=True; break
        pos+=12+length
    if not ended or header is None: raise ValueError('missing PNG header/end')
    w,h,depth,color,compression,filtering,interlace=header
    if (depth,color,compression,filtering,interlace)!=(8,2,0,0,0):
        raise ValueError(f'unsupported PNG encoding: {header}')
    raw=zlib.decompress(compressed); stride=w*3
    if len(raw)!=h*(stride+1): raise ValueError('bad decompressed size')
    pixels=bytearray(); previous=bytearray(stride)
    for y in range(h):
        offset=y*(stride+1); kind=raw[offset]; row=bytearray(raw[offset+1:offset+1+stride])
        for x in range(stride):
            a=row[x-3] if x>=3 else 0; b=previous[x]; c=previous[x-3] if x>=3 else 0
            if kind==0: predictor=0
            elif kind==1: predictor=a
            elif kind==2: predictor=b
            elif kind==3: predictor=(a+b)//2
            elif kind==4:
                p=a+b-c; distances=(abs(p-a),abs(p-b),abs(p-c))
                predictor=(a,b,c)[distances.index(min(distances))]
            else: raise ValueError('bad PNG filter')
            row[x]=(row[x]+predictor)&255
        pixels.extend(row); previous=row
    return w,h,bytes(pixels)

def compare(a,b):
    aa=decode(a); bb=decode(b)
    if aa[:2]!=bb[:2]: raise AssertionError(f'dimensions differ: {aa[:2]} vs {bb[:2]}')
    mismatches=sum(x!=y for x,y in zip(aa[2],bb[2]))
    if mismatches: raise AssertionError(f'{mismatches} decoded channel values differ')
    return dict(width=aa[0],height=aa[1],decoded_rgb_sha256=hashlib.sha256(aa[2]).hexdigest(),mismatched_channels=0)
