from coilsnake.model.eb.blocks import EbCompressibleBlock
from coilsnake.model.eb.graphics import EbTileArrangement, EbGraphicTileset
from coilsnake.model.eb.palettes import EbPalette
from coilsnake.util.common.image import open_indexed_image
from coilsnake.util.common.yml import yml_load, yml_dump
from coilsnake.util.eb.pointer import from_snes_address, read_asm_pointer, write_asm_pointer, to_snes_address


EB_IMAGE_PALETTE = EbPalette(1, 2)
EB_IMAGE_PALETTE[0, 0].from_tuple((255, 255, 255))
EB_IMAGE_PALETTE[0, 1].from_tuple((0, 0, 0))

M2_FLYOVER_IMAGE_PALETTE = EbPalette(1, 2)
M2_FLYOVER_IMAGE_PALETTE[0, 0].from_tuple((0, 0, 0))
M2_FLYOVER_IMAGE_PALETTE[0, 1].from_tuple((255, 255, 255))

M2_DOSEI_IMAGE_PALETTE = EbPalette(1, 4)
M2_DOSEI_IMAGE_PALETTE[0, 0].from_tuple((255, 0, 255)) # unused
M2_DOSEI_IMAGE_PALETTE[0, 1].from_tuple((255, 255, 255))
M2_DOSEI_IMAGE_PALETTE[0, 2].from_tuple((0, 255, 255)) # unused
M2_DOSEI_IMAGE_PALETTE[0, 3].from_tuple((0, 0, 0))

FONT_IMAGE_ARRANGEMENT_WIDTH = 16
_FONT_IMAGE_ARRANGEMENT_DOSEI = EbTileArrangement(width=16, height=16)
_FONT_IMAGE_ARRANGEMENT_96 = EbTileArrangement(width=FONT_IMAGE_ARRANGEMENT_WIDTH, height=6)
_FONT_IMAGE_ARRANGEMENT_128 = EbTileArrangement(width=FONT_IMAGE_ARRANGEMENT_WIDTH, height=8)
_FONT_IMAGE_ARRANGEMENT_224 = EbTileArrangement(width=FONT_IMAGE_ARRANGEMENT_WIDTH, height=14)
_FONT_IMAGE_ARRANGEMENT_512 = EbTileArrangement(width=FONT_IMAGE_ARRANGEMENT_WIDTH, height=32)
ARRANGEMENT_BY_NUM_CHARS = {
    64: _FONT_IMAGE_ARRANGEMENT_DOSEI,
    96: _FONT_IMAGE_ARRANGEMENT_96,
    128: _FONT_IMAGE_ARRANGEMENT_128,
    224: _FONT_IMAGE_ARRANGEMENT_224,
    512: _FONT_IMAGE_ARRANGEMENT_512,
}

def _configure_font_arrangement(arrangement):
    i = 0
    for y in range(arrangement.height):
        for x in range(arrangement.width):
            arrangement[x, y].tile = i
            i += 1
for arrangement in ARRANGEMENT_BY_NUM_CHARS.values():
    _configure_font_arrangement(arrangement)


class EbFont(object):
    def __init__(self, num_characters=96, orig_characters=96, char_tile_ratio=1, tile_width=16, tile_height=8, palette=EB_IMAGE_PALETTE, clear_color=1, bpp=1):
        self.num_characters = num_characters
        self.orig_characters = orig_characters
        self.char_tile_ratio = char_tile_ratio
        self.clear_color = clear_color
        self.bpp = bpp
        self.palette = palette
        num_tiles = num_characters * char_tile_ratio * char_tile_ratio
        self.tileset = EbGraphicTileset(num_tiles=num_tiles, tile_width=tile_width, tile_height=tile_height)
        self.character_widths = None
        self.arrangement = ARRANGEMENT_BY_NUM_CHARS[num_characters]

    def from_block(self, block, tileset_offset, character_widths_offset):
        self.tileset.from_block(block=block, offset=tileset_offset, bpp=self.bpp)
        if self.char_tile_ratio != 1:
            tw = self.arrangement.width
            cw = tw // self.char_tile_ratio
            for c_idx in range(self.orig_characters, self.num_characters):
                cx = c_idx % cw
                cy = c_idx // cw
                tx, ty = cx * self.char_tile_ratio, cy * self.char_tile_ratio
                for j in range(self.char_tile_ratio):
                    for i in range(self.char_tile_ratio):
                        self.tileset.clear_tile(tx + i + (ty + j) * tw, color=self.clear_color)
        else:
            for i in range(self.orig_characters, self.num_characters):
                self.tileset.clear_tile(i, color=self.clear_color)
        if character_widths_offset is not None:
            self.character_widths = block[character_widths_offset:character_widths_offset + self.orig_characters].to_list()
            self.character_widths += [255] * (self.num_characters - self.orig_characters)

    def to_block(self, block):
        tileset_offset = block.allocate(size=self.tileset.block_size(bpp=self.bpp))
        self.tileset.to_block(block=block, offset=tileset_offset, bpp=self.bpp)

        character_widths_offset = None
        if self.character_widths is not None:
            character_widths_offset = block.allocate(size=self.num_characters)
            block[character_widths_offset:character_widths_offset + self.num_characters] = self.character_widths

        return tileset_offset, character_widths_offset

    def to_files(self, image_file, widths_file, image_format="png", widths_format="yml"):
        image = self.arrangement.image(self.tileset, self.palette)
        image.save(image_file, image_format)
        del image

        if self.character_widths is not None:
            character_widths_dict = dict(enumerate(self.character_widths))
            if widths_format == "yml":
                yml_dump(character_widths_dict, widths_file, default_flow_style=False)

    def from_files(self, image_file, widths_file, image_format="png", widths_format="yml"):
        image = open_indexed_image(image_file)
        self.tileset.from_image(image, self.arrangement, self.palette)
        del image

        if widths_file is not None:
            if widths_format == "yml":
                widths_dict = yml_load(widths_file)
                self.character_widths = [widths_dict[i] for i in range(self.tileset.num_tiles_maximum if self.char_tile_ratio == 1 else self.num_characters)]

    def image_size(self):
        arr = self.arrangement
        return arr.width * self.tileset.tile_width, arr.height * self.tileset.tile_height


_CREDITS_PREVIEW_SUBPALETTES = [
    [1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1],
    [1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]]
_CREDITS_PREVIEW_SUBPALETTES_M2 = [
    [1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0],
    [1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]]
_CREDITS_PREVIEW_ARRANGEMENT = EbTileArrangement(width=16, height=12)
for y in range(_CREDITS_PREVIEW_ARRANGEMENT.height):
    for x in range(_CREDITS_PREVIEW_ARRANGEMENT.width):
        _CREDITS_PREVIEW_ARRANGEMENT[x, y].tile = y * _CREDITS_PREVIEW_ARRANGEMENT.width + x
        _CREDITS_PREVIEW_ARRANGEMENT[x, y].subpalette = _CREDITS_PREVIEW_SUBPALETTES_M2[y][x]


class EbCreditsFont(object):
    def __init__(self):
        self.tileset = EbGraphicTileset(num_tiles=192, tile_width=8, tile_height=8)
        self.palette = EbPalette(num_subpalettes=2, subpalette_length=4)

    def from_block(self, block, tileset_asm_pointer_offset, palette_offset):
        with EbCompressibleBlock() as compressed_block:
            compressed_block.from_compressed_block(block=block, offset=from_snes_address(
                read_asm_pointer(block=block, offset=tileset_asm_pointer_offset)))
            self.tileset.from_block(block=compressed_block, bpp=2)
        self.palette.from_block(block=block, offset=palette_offset)

    def to_block(self, block, tileset_asm_pointer_offset, palette_offset):
        tileset_block_size = self.tileset.block_size(bpp=2)
        with EbCompressibleBlock(tileset_block_size) as compressed_block:
            self.tileset.to_block(block=compressed_block, offset=0, bpp=2)
            compressed_block.compress()
            tileset_offset = block.allocate(data=compressed_block)
            write_asm_pointer(block=block, offset=tileset_asm_pointer_offset, pointer=to_snes_address(tileset_offset))
        self.palette.to_block(block=block, offset=palette_offset)

    def to_files(self, image_file, image_format="png"):
        image = _CREDITS_PREVIEW_ARRANGEMENT.image(self.tileset, self.palette)
        image.save(image_file, image_format)
        del image

    def from_files(self, image_file, image_format="png"):
        image = open_indexed_image(image_file)
        self.palette.from_image(image)
        self.tileset.from_image(image, _CREDITS_PREVIEW_ARRANGEMENT, self.palette)
        del image