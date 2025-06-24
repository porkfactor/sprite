import sys
import argparse
from pathlib import Path
from PIL import Image

class pixel():
    def __init__(self, r: int, g: int, b: int, a: int=0):
        self._r = int(r)
        self._g = int(g)
        self._b = int(b)
        self._a = int(a)

    def __repr__(self) -> str:
        return f'{{r={self._r}, g={self._g}, b={self._b}, a={self._a}}}'

    @property
    def r(self) -> int:
        return self._r

    @property
    def g(self) -> int:
        return self._g

    @property
    def b(self) -> int:
        return self._b

    @property
    def a(self) -> int:
        return self._a
    
    @property
    def rgb565(self) -> int:
        if self._a:
            return ((self._r >> 3) << 11) | ((self._g >> 2) << 5) | (self._b >> 3)
        else:
            return 0

class region:
    def __init__(self, x, y, width, height, data):
        self._x: int = x
        self._y: int = y
        self._width: int = width
        self._height: int = height
        self._data: list[pixel] = data

        if len(self._data) != width * height:
            raise BufferError

    @property
    def x(self) -> int:
        return self._x

    @property
    def y(self) -> int:
        return self._y

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height
    
    @property
    def data(self) -> list[pixel]:
        return self._data
    
    def __repr__(self) -> str:
        return f'{self._x} {self._y} {self._width} {self._height}'

    def getpixel(self, x: int, y: int) -> pixel:
        return self._data[(y * self._width) + x]

    def subregion(self, x: int, y: int, width: int, height: int):
        if x + width > self._width:
            raise IndexError
        
        if y + height > self._height:
            raise IndexError

        data: list[pixel] = []

        for row in range(height):
            start = ((y + row) * self._width) + x
            end = start + width
            data.extend(self._data[start:end])

        return region(x=self._x + x, y=self._y + y, width=width, height=height, data=data)

    def split_x(self, min_width=None) -> list:
        columns: list = []
        in_column: bool = False
        column_start: int = 0
        column_end: int = 0

        for x in range(self._width):
            empty = True

            for y in range(self._height):
                p: pixel = self.getpixel(x=x, y=y)
                if p.a != 0:
                    empty = False
                    break
            
            if empty and in_column:
                in_column = False
                column_end = x - 1
                columns.append(self.subregion(x=column_start, y=0, width=column_end - column_start + 1, height=self.height))
            elif not empty and not in_column:
                in_column = True
                column_start = x

        return columns if columns else [self]

    def split_y(self, min_height=None) -> list:
        rows: list = []
        in_row: bool = False
        row_start: int = 0
        row_end: int = 0

        for y in range(self._height):
            empty = True

            for x in range(self._width):
                p: pixel = self.getpixel(x=x, y=y)
                if p.a != 0:
                    empty = False
                    break

            if empty and in_row:
                in_row = False
                row_end = y - 1
                rows.append(self.subregion(x=0, y=row_start, width=self._width, height=row_end - row_start + 1))
            elif not empty and not in_row:
                in_row = True
                row_start = y

        return rows if rows else [self]

    def split_yx(self, min_width=None, min_height=None) -> list:
        blocks: list[region] = []

        for row in self.split_y(min_height=min_height):
            blocks.extend(row.split_x(min_width=min_width))

        return blocks if blocks else [self]
    
    @staticmethod
    def split(x: int, y: int, width: int, height: int, data: list, min_width: int=None, min_height: int=None) -> list:
        r = region(x=x, y=y, width=width, height=height, data=data)
        return r.split_yx(min_width=min_width, min_height=min_height)

def save_bitmap(block: region, filename: Path):
    with open(file=filename, mode='wb') as f:
        i = Image.new(mode='RGBA', size=(block.width, block.height))
        i.putdata([(p.r, p.g, p.b, p.a) for p in block.data])
        i.save(fp=f, format='png')

def write_array(f, bitmap: list[int], width: int=16, wrap: int=8):
    w=int(width/4)
    for i in range(len(bitmap)):
        if (i % wrap) == 0:
            if i != 0:
                f.write('\n')
            f.write('    ')
        else:
            f.write(' ')
        f.write(f'0x{bitmap[i]:0{w}x},')
    f.write('\n')

def write_bitarray(f, block: region, width: int=8, wrap: int=8):
    bitmap = []
    val: int = 0
    for i in range(len(block.data)):
        if block.data[i].a:
            val |= (1 << (i % width))

        if (i != 0) and ((i % width) == 0):
            bitmap.append(val)
            val = 0
    
    write_array(f, bitmap, width=width, wrap=wrap)

def save_c_decl(f, slug: str, block: region):
    f.write(f'static size_t const {slug}_width = {block.width};\n')
    f.write(f'static size_t const {slug}_height = {block.height};\n')
    f.write(f'static uint16_t const {slug}_rgb565[] PROGMEM =\n')
    f.write(f'{{\n')
    write_array(f, [p.rgb565 for p in block.data])
    f.write(f'}};\n')

    f.write(f'static uint8_t const {slug}_mask[] PROGMEM =\n')
    f.write(f'{{\n')
    write_bitarray(f, block)
    f.write(f'}};\n')

def write_header(f, slug: str, blocks: list[region]):
    f.write(f'#ifndef {slug.upper()}_H_\n')
    f.write(f'#define {slug.upper()}_H_\n')
    f.write('\n')

    i = 0
    for block in blocks:
        save_c_decl(f, slug=f'{slug}_image_{i}', block=block)
        i = i + 1

    f.write('\n')
    f.write(f'#endif\n')

def save_header(filename: str, blocks: list[region]):
    guard = filename.upper().replace('.', '_')

    with open(filename, 'w') as f:
        save_header(f, blocks=blocks, guard=guard)

def safe_identifier(s: str):
    return s.replace('.', '_')

def main(input: Path, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    blocks = []
    with Image.open(input) as im:
        im = im.convert(mode='RGBA')

        data=[pixel(b[0], b[1], b[2], b[3]) for b in im.getdata()]

        print(f'height={im.height} width={im.width} thing={im.width * im.height} len={len(data)}')
        blocks.extend(region.split(x=0, y=0, width=im.width, height=im.height, data=data))

    with open(f'{safe_identifier(str(input.name))}.h', 'w') as f:
        write_header(f, blocks=blocks, slug=safe_identifier(str(input.name)))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', action='store', dest='input', required=True)
    parser.add_argument('--output', action='store', dest='output', default='.')

    try:
        args = parser.parse_args()
    except Exception as e:
        print(f'{e}')
        exit(1)
    else:
        main(input=Path(args.input), output=Path(args.output))
