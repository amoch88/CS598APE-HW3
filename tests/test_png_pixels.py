import pathlib,struct,sys,tempfile,unittest,zlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from png_pixels import decode

class PNGTests(unittest.TestCase):
    def test_all_filters_and_crc(self):
        w,h=4,5; expected=bytes((i*73+19)%256 for i in range(w*h*3)); raw=bytearray(); stride=w*3
        for y in range(h):
            row=expected[y*stride:(y+1)*stride]; previous=expected[(y-1)*stride:y*stride] if y else bytes(stride)
            raw.append(y)
            for x,value in enumerate(row):
                left=row[x-3] if x>=3 else 0; above=previous[x]; upper_left=previous[x-3] if x>=3 else 0
                if y==0: pred=0
                elif y==1: pred=left
                elif y==2: pred=above
                elif y==3: pred=(left+above)//2
                else:
                    p=left+above-upper_left
                    pa,pb,pc=abs(p-left),abs(p-above),abs(p-upper_left)
                    pred=left if pa<=pb and pa<=pc else above if pb<=pc else upper_left
                raw.append((value-pred)%256)
        def chunk(tag,data): return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
        with tempfile.TemporaryDirectory() as directory:
            path=pathlib.Path(directory)/'fixture.png'; path.write_bytes(png)
            self.assertEqual(decode(path),(w,h,expected))
            corrupted=bytearray(png); corrupted[29]^=1; path.write_bytes(corrupted)
            with self.assertRaisesRegex(ValueError,'CRC'): decode(path)
if __name__=='__main__': unittest.main()
