import io
from pathlib import Path
from PIL import Image
from dataclasses import dataclass

@dataclass
class pixel():
    r: int
    g: int
    b: int
    a: int

@dataclass
class block():
    x: int
    y: int
    width: int
    height: int

def condense_block(im: Image, block: list[int]):
    pass

def split_columns(b: block, min_width=None) -> list[block]:
    columns: list[block] = []
    in_column: bool = False
    column_start: int = 0
    column_end: int = 0

    for x in range(b.width):
        empty = True

        for y in range(b.height):
            p: pixel = b.getpixel(x=x, y=y)
            if p.a != 0:
                empty = False
                break
        
        if empty and in_column:
            in_column = False
            column_end = y - 1
            columns.append(column_start, column_end)
        elif not empty and not in_column:
            in_column = True
            column_start = y

    return columns

def split_rows(b: block, min_height=None) -> list[block]:
    rows: list[block] = []
    in_row: bool = False
    row_start: int = 0
    row_end: int = 0

    for y in range(b.height):
        empty = True

        for x in range(b.width):
            p: pixel = b.getpixel(x=x, y=y)
            if p.a != 0:
                empty = False
                break

        if empty and in_row:
            in_row = False
            row_end = y - 1
            rows.append(row_start, row_end)
        elif not empty and not in_row:
            in_row = True
            row_start = y

    return rows

def split_block(b: block, min_width=None, min_height=None) -> list[block]:
    blocks: list[block] = []

    for row in split_rows(b, min_width=min_width, min_height=min_height):
        blocks.append(split_columns(row, min_width=min_width, min_height=min_height))

    return blocks

def main():
    filename: Path = 'turrican.png'
    with Image.open(filename) as im:
        im = im.convert(mode='RGBA')

        bands = []
        in_band: bool = False
        band_start: int = 0
        band_end: int = 0

        for y in range(im.height):
            blank = True
            for x in range(im.width):
                p = im.getpixel(xy=(x, y))
                if p != (255, 0, 255, 0):
                    blank = False
                    break
            if blank:
                if in_band:
                    in_band = False
                    band_end = y - 1
                    bands.append((band_start, band_end))
            else:
                if not in_band:
                    in_band = True
                    band_start = y
        
        blocks = []

        for band in bands:
            print(band)
            in_column = False
            column_start: int = 0
            column_end: int = 0

            for x in range(im.width):
                blank = True

                for y in range(band[0], band[1]):
                    p = im.getpixel(xy=(x, y))
                    if p != (255, 0, 255, 0):
                        blank = False
                        break

                if blank:
                    if in_column:
                        in_column = False
                        column_end = x - 1
                        blocks.append((column_start, column_end, band[0], band[1]))
                else:
                    if not in_column:
                        in_column = True
                        column_start = x
            break

        for block in blocks:
            print(block)

if __name__ == '__main__':
    main()
