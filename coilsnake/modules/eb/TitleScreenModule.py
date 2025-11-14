import logging

from coilsnake.model.common.blocks import Block
from coilsnake.model.eb.blocks import EbCompressibleBlock
from coilsnake.model.eb.graphics import EbGraphicTileset, EbTileArrangement
from coilsnake.model.eb.palettes import EbPalette
from coilsnake.model.eb.title_screen import TitleScreenLayoutEntry, \
    CHARS_NUM_TILES
from coilsnake.modules.eb.EbModule import EbModule
from coilsnake.util.common.image import open_indexed_image
from coilsnake.util.common.yml import yml_dump, yml_load
from coilsnake.util.eb.pointer import (
    from_snes_address, to_snes_address,
    PointerReference, AsmPointerReference, XlPointerReference,
)
from coilsnake.ui.language import global_strings as strings
from coilsnake.ui.language import getLogger

log = logging.getLogger(__name__)

# Background data pointers
# ebsrc has this labeled wrong for Mother 2
BG1_TILESET_POINTER = AsmPointerReference(0xEC5E) #EBF2
BG2_TILESET_POINTER = AsmPointerReference(0xEC32)
BG1_ARRANGEMENT_POINTER = AsmPointerReference(0xECDF) #EC1D
BG2_ARRANGEMENT_POINTER = AsmPointerReference(0xECB3)
# This is the animated palette in M2
# It is the entire palette (all 256 entries)
# times 9 palette animations
ALL_PALETTE_POINTER = AsmPointerReference(0xED0B) #ECC6

# Background data parameters
BG_ARRANGEMENT_WIDTH = 32
BG_ARRANGEMENT_HEIGHT = 32
BG_SUBPALETTE_LENGTH = 16 #256 for EB
BG_NUM_ANIM_SUBPALETTES = 20
BG_NUM_TILES = 704
BG_TILESET_BPP = 4

# Characters data pointers
CHARS_TILESET_POINTER = AsmPointerReference(0xEC89) #EC49
CHARS_SPRITEMAP_TABLE_POINTER = XlPointerReference(0x4217B, 0x1C) #0x4220E in US

# Characters data parameters
CHARS_SUBPALETTE_LENGTH = 16
CHARS_NUM_ANIM_SUBPALETTES = 14
CHARS_TILESET_BPP = 4

# Commmon parameters
NUM_ANIM_FRAMES = 9
NUM_CHARS = 7
NUM_SUBPALETTES = 16
TILE_WIDTH = 8
TILE_HEIGHT = 8

# Project file paths
BG1_FRAMES_PATH = "TitleScreen/Background/BG1_{:02d}"
BG2_FRAMES_PATH = "TitleScreen/Background/BG2_{:02d}"
BG_INITIAL_FLASH_PATH = "TitleScreen/Background/InitialFlash"
CHARS_FRAMES_PATH = "TitleScreen/Chars/{:02d}"
CHARS_INITIAL_PATH = "TitleScreen/Chars/Initial"
CHARS_POSITIONS_PATH = "TitleScreen/Chars/positions"

# Palette division
BG1_SLICE = slice(0, BG_SUBPALETTE_LENGTH*7)
BG2_SLICE = slice(BG_SUBPALETTE_LENGTH*7, BG_SUBPALETTE_LENGTH*8)
OBJ_SLICE = slice(BG_SUBPALETTE_LENGTH*8, BG_SUBPALETTE_LENGTH*16)

class TitleScreenModule(EbModule):
    """Extracts the title screen data from EarthBound.

    This module allows for the editing of the background and characters
    of the title screen. The slide-in animation for the characters is
    controlled through assembly, while the rest of the animation works
    by changing between several palettes (one for each new frame of
    animation) and keeping the same tileset for each frame.
    """

    NAME = "Title Screen"
    FREE_RANGES = [
        (0x21A0A0, 0x21B18B),  # Background Tileset - 0x21B211, 0x21C6E4
        (0x21B2C7, 0x21BB00),  # Background Arrangement - 0x21AF7D, 0x21B210
        (0x21C291, 0x21C46F),  # Background Palette - 0x21CDE1, 0x21CE07
        #(),  # Background Animated Palette - 0x21AEFD, 0x21AF7C

        (0x21BB01, 0x21C290),  # Characters Tileset - 0x21C6E5, 0x21CDE0
        (0x21C80D, 0x21CA59),  # Characters Spritemap - 0x21CE08, ...?
        #(),  # Characters Palette - 0x21AE7C, 0x21AE82
        #(),  # Characters Animated Palette - 0x21AE83, 0x21AEFC

        #()  # Animation Data - 0x21CE08, 0x21CF9C
    ]

    def __init__(self):
        super(TitleScreenModule, self).__init__()

        # Background data (includes the central "B", the copyright
        # notice and the glow around the letters)
        self.bg1_tileset = EbGraphicTileset(
            num_tiles=1024, tile_width=TILE_WIDTH,
            tile_height=TILE_HEIGHT
        )
        self.bg1_arrangement = EbTileArrangement(
            width=BG_ARRANGEMENT_WIDTH, height=BG_ARRANGEMENT_HEIGHT
        )
        self.bg1_anim_palette = EbPalette(
            num_subpalettes=NUM_ANIM_FRAMES,
            subpalette_length=BG_SUBPALETTE_LENGTH * 7
        )
        self.bg2_tileset = EbGraphicTileset(
            num_tiles=1024, tile_width=TILE_WIDTH,
            tile_height=TILE_HEIGHT
        )
        self.bg2_arrangement = EbTileArrangement(
            width=BG_ARRANGEMENT_WIDTH, height=BG_ARRANGEMENT_HEIGHT
        )
        self.bg2_anim_palette = EbPalette(
            num_subpalettes=NUM_ANIM_FRAMES,
            subpalette_length=BG_SUBPALETTE_LENGTH
        )

        # Characters data (the title screen's animated letters)
        self.chars_tileset = EbGraphicTileset(
            num_tiles=CHARS_NUM_TILES, tile_width=TILE_WIDTH,
            tile_height=TILE_HEIGHT
        )
        self.chars_anim_palette = EbPalette(
            num_subpalettes=CHARS_NUM_ANIM_SUBPALETTES,
            subpalette_length=CHARS_SUBPALETTE_LENGTH * 8
        )
        self.chars_layouts = [[] for _ in range(NUM_CHARS)]

    def read_from_rom(self, rom):
        self.read_palettes_from_rom(rom)
        self.read_background_data_from_rom(rom)
        self.read_chars_data_from_rom(rom)
        self.read_chars_layouts_from_rom(rom)

    def read_palettes_from_rom(self, rom):
        # The animations actually play out in this order due to probably a bug
        # in the code: 0 2 4 6 8 1 3 5 0
        # We are going to dump them in the proper order with all the data, and
        # also hopefully give the ability to fix the bugs with the animation
        with EbCompressibleBlock() as block:
            # Read the background palette data
            # This contains a full (256-colour) palettes for each of the 9x
            # animation frames.
            self._decompress_block(rom, block, ALL_PALETTE_POINTER)
            all_palette = EbPalette(
                num_subpalettes=NUM_ANIM_FRAMES,
                subpalette_length=BG_SUBPALETTE_LENGTH * 16
            )
            all_palette.from_block(block=block, offset=0)
            for anim in range(NUM_ANIM_FRAMES):
                self.bg1_anim_palette[anim, :] = all_palette[anim, BG1_SLICE]
                self.bg2_anim_palette[anim, :] = all_palette[anim, BG2_SLICE]
                self.chars_anim_palette[anim, :] = all_palette[anim, OBJ_SLICE]
        pass

    def read_background_data_from_rom(self, rom):
        with EbCompressibleBlock() as block:
            # BG1
            # Read the background tileset data
            self._decompress_block(rom, block, BG1_TILESET_POINTER)
            self.bg1_tileset.from_block(
                block=block, offset=0, bpp=BG_TILESET_BPP
            )

            # Read the background tile arrangement data
            self._decompress_block(rom, block, BG1_ARRANGEMENT_POINTER)
            self.bg1_arrangement.from_block(block=block, offset=0)

            # BG2
            # Read the background tileset data
            self._decompress_block(rom, block, BG2_TILESET_POINTER)
            self.bg2_tileset.from_block(
                block=block, offset=0, bpp=BG_TILESET_BPP
            )

            # Read the background tile arrangement data
            self._decompress_block(rom, block, BG2_ARRANGEMENT_POINTER)
            self.bg2_arrangement.from_block(block=block, offset=0)

    def read_chars_data_from_rom(self, rom):
        with EbCompressibleBlock() as block:
            # Read the characters tileset data
            self._decompress_block(rom, block, CHARS_TILESET_POINTER)
            self.chars_tileset.from_block(
                block=block, offset=0, bpp=CHARS_TILESET_BPP
            )

    def read_chars_layouts_from_rom(self, rom):
        chars_spritemap_table_address_snes = CHARS_SPRITEMAP_TABLE_POINTER.read(rom)
        chars_spritemap_bank = chars_spritemap_table_address_snes & 0xFF_0000
        chars_spritemap_table_offset = from_snes_address(chars_spritemap_table_address_snes)

        self.chars_layouts = [[] for _ in range(NUM_CHARS)]
        for char in range(NUM_CHARS):
            # Get the location of a character's data
            address = chars_spritemap_bank | rom.read_multi(
                chars_spritemap_table_offset + char*2, 2
            )

            # Read entries until a final entry is encountered
            while True:
                entry = TitleScreenLayoutEntry()
                entry.from_block(rom, from_snes_address(address))
                self.chars_layouts[char].append(entry)
                address += 5
                if entry.is_final():
                    break

    def write_to_rom(self, rom):
        self.write_palette_to_rom(rom)
        self.write_background_data_to_rom(rom)
        self.write_chars_data_to_rom(rom)
        self.write_chars_layouts_to_rom(rom)

    def write_palette_to_rom(self, rom):
        all_palette = EbPalette(
            num_subpalettes=NUM_ANIM_FRAMES,
            subpalette_length=BG_SUBPALETTE_LENGTH * 16
        )
        for anim in range(NUM_ANIM_FRAMES):
            all_palette[anim, BG1_SLICE] = self.bg1_anim_palette[anim, :]
            all_palette[anim, BG2_SLICE] = self.bg2_anim_palette[anim, :]
            all_palette[anim, OBJ_SLICE] = self.chars_anim_palette[anim, :]
        block_size = all_palette.block_size()
        with EbCompressibleBlock(block_size) as block:
            all_palette.to_block(block=block, offset=0)
            self._write_compressed_block(rom, block, ALL_PALETTE_POINTER)

    def write_background_data_to_rom(self, rom):
        # BG1
        # Write the background tileset data
        block_size = self.bg1_tileset.block_size(bpp=BG_TILESET_BPP)
        with EbCompressibleBlock(block_size) as block:
            self.bg1_tileset.to_block(block=block, offset=0, bpp=BG_TILESET_BPP)
            self._write_compressed_block(rom, block, BG1_TILESET_POINTER)

        # Write the background tile arrangement data
        block_size = self.bg1_arrangement.block_size()
        with EbCompressibleBlock(block_size) as block:
            self.bg1_arrangement.to_block(block=block, offset=0)
            self._write_compressed_block(rom, block, BG1_ARRANGEMENT_POINTER)

        # BG2
        # Write the background tileset data
        block_size = self.bg2_tileset.block_size(bpp=BG_TILESET_BPP)
        with EbCompressibleBlock(block_size) as block:
            self.bg2_tileset.to_block(block=block, offset=0, bpp=BG_TILESET_BPP)
            self._write_compressed_block(rom, block, BG2_TILESET_POINTER)

        # Write the background tile arrangement data
        block_size = self.bg2_arrangement.block_size()
        with EbCompressibleBlock(block_size) as block:
            self.bg2_arrangement.to_block(block=block, offset=0)
            self._write_compressed_block(rom, block, BG2_ARRANGEMENT_POINTER)

    def write_chars_data_to_rom(self, rom):
        # Write the characters tileset data
        block_size = self.chars_tileset.block_size(bpp=CHARS_TILESET_BPP)
        with EbCompressibleBlock(block_size) as block:
            self.chars_tileset.to_block(
                block=block, offset=0, bpp=CHARS_TILESET_BPP
            )
            self._write_compressed_block(rom, block, CHARS_TILESET_POINTER)

    def write_chars_layouts_to_rom(self, rom):
        block_size = sum(
            TitleScreenLayoutEntry.block_size()*len(c)
            for c in self.chars_layouts
        ) + 2 * len(self.chars_layouts)

        # Ensure the new data is located in only one bank
        # Spreading it across two banks might make part of it inaccessible.
        def can_write_to(begin):
            return begin >> 16 == (begin + block_size) >> 16
        rom_offset = rom.allocate(
            size=block_size,
            can_write_to=can_write_to
        )
        block_addr = to_snes_address(rom_offset)

        with Block(block_size) as block:
            # Write the character animation data to the ROM
            offset = 0
            chars_addrs = []
            for layout in self.chars_layouts:
                chars_addrs.append(block_addr + offset)
                for entry in layout:
                    entry.to_block(block=block, offset=offset)
                    offset += entry.block_size()
            spritemap_table_addr = block_addr + offset

            # Write the spritemap table
            for char_num, char_addr in enumerate(chars_addrs):
                block.write_multi(offset + char_num * 2, char_addr & 0xFFFF, 2)

            # Write the new data block into the ROM
            rom[rom_offset:rom_offset+block_size] = block

        # Update the spritemap table pointer
        CHARS_SPRITEMAP_TABLE_POINTER.write(rom, spritemap_table_addr)

    def read_from_project(self, resource_open):
        self.read_background_data_from_project(resource_open)
        self.read_chars_data_from_project(resource_open)

    def read_background_data_from_project(self, resource_open):
        # BG1
        # Read the background animated frames
        for frame in range(NUM_ANIM_FRAMES):
            # Create temporary structures used to check consistency between
            # frames
            tileset = EbGraphicTileset(BG_NUM_TILES, TILE_WIDTH, TILE_HEIGHT)
            arrangement = EbTileArrangement(
                BG_ARRANGEMENT_WIDTH, BG_ARRANGEMENT_HEIGHT
            )
            palette = EbPalette(NUM_SUBPALETTES, BG_SUBPALETTE_LENGTH)

            # Read one frame's image data
            with resource_open(BG1_FRAMES_PATH.format(frame), "png") as f:
                image = open_indexed_image(f)
                if frame == 0:
                    self.bg1_arrangement.from_image(
                        image, self.bg1_tileset, palette
                    )
                else:
                    arrangement.from_image(image, tileset, palette)

            self.bg1_anim_palette.subpalettes[frame] = palette.flatten_subpalettes()[0:7*16]
            # For frame 0, grab all the data. For future frames, also compare
            # the tileset and arrangement against frame 0
            if frame == 0:
                continue

            if self.bg1_tileset != tileset:
                log.warn(
                    strings.get("console_warning_tileset_reference").format(frame)
                )
            if self.bg1_arrangement != arrangement:
                log.warn(
                    "Arrangement from background frame {} does not match "
                    "reference.".format(frame)
                )

        # BG2
        # Read the background animated frames
        for frame in range(NUM_ANIM_FRAMES):
            # Create temporary structures used to check consistency between
            # frames
            tileset = EbGraphicTileset(BG_NUM_TILES, TILE_WIDTH, TILE_HEIGHT)
            arrangement = EbTileArrangement(
                BG_ARRANGEMENT_WIDTH, BG_ARRANGEMENT_HEIGHT
            )
            palette = EbPalette(NUM_SUBPALETTES, BG_SUBPALETTE_LENGTH)

            # Read one frame's image data
            with resource_open(BG2_FRAMES_PATH.format(frame), "png") as f:
                image = open_indexed_image(f)
                if frame == 0:
                    self.bg2_arrangement.from_image(
                        image, self.bg2_tileset, palette
                    )
                else:
                    arrangement.from_image(image, tileset, palette)

            self.bg2_anim_palette.subpalettes[frame] = palette.flatten_subpalettes()[0:16]
            # For frame 0, grab all the data. For future frames, also compare
            # the tileset and arrangement against frame 0
            if frame == 0:
                continue

            if self.bg2_tileset != tileset:
                log.warn(
                    "Tileset from background frame {} does not match "
                    "reference.".format(frame)
                )
            if self.bg2_arrangement != arrangement:
                log.warn(
                    "Arrangement from background frame {} does not match "
                    "reference.".format(frame)
                )

        # Fix up BG2 arrangement to use the correct palettes.
        for row in self.bg2_arrangement.arrangement:
            for tile in row:
                tile.subpalette = 7

    @staticmethod
    def add_to_tile_index(idx, x, y):
        xp = idx & 0x0F
        yp = idx & 0xF0
        xp = (xp + x) & 0x0F
        yp = (yp + (y << 4)) & 0xF0
        return xp | yp

    def read_chars_data_from_project(self, resource_open):
        # Read the characters positions
        with resource_open(CHARS_POSITIONS_PATH, "yml", True) as f:
            chars_positions = yml_load(f)

        # Read the characters animated frames
        self.chars_tileset = None
        original_tileset = None
        for p in range(NUM_ANIM_FRAMES):
            # Read one of the animation frames
            with resource_open(CHARS_FRAMES_PATH.format(p), "png") as f:
                # Create temporary structures to hold the data
                image = open_indexed_image(f)
                arrangement = EbTileArrangement(
                    image.width // TILE_WIDTH, image.height // TILE_HEIGHT
                )
                tileset = EbGraphicTileset(
                    CHARS_NUM_TILES, TILE_WIDTH, TILE_HEIGHT
                )
                anim_subpalette = EbPalette(
                    NUM_SUBPALETTES, CHARS_SUBPALETTE_LENGTH
                )
                # TODO: allow flip
                arrangement.from_image(image, tileset, anim_subpalette, True)

            # Add the characters animation subpalette
            self.chars_anim_palette.subpalettes[p] = anim_subpalette.flatten_subpalettes()[0:8*16]

            # Add the characters tileset if not already set, otherwise
            # ensure that it the current tileset is identical
            if not self.chars_tileset:
                original_tileset = tileset
                self.chars_tileset = EbGraphicTileset(
                    CHARS_NUM_TILES, TILE_WIDTH, TILE_HEIGHT
                )
                self.chars_tileset.tiles = [
                    [[0 for _ in range(TILE_HEIGHT)]
                        for _ in range(TILE_WIDTH)]
                    for _ in range(CHARS_NUM_TILES)
                ]
                unused_tiles = set(range(CHARS_NUM_TILES))

                # Set the new character layouts
                self.chars_layouts = [[] for _ in range(NUM_CHARS)]
                for c, data in chars_positions.items():
                    # Get the data from the YAML file
                    x = int(data['x'] // TILE_WIDTH)
                    y = int(data['y'] // TILE_HEIGHT)
                    width = int(data['width'] // TILE_WIDTH)
                    height = int(data['height'] // TILE_HEIGHT)
                    x_offset = data['top_left_offset']['x']
                    y_offset = data['top_left_offset']['y']
                    unknown = data['unknown']

                    # Generate a list of all tiles must be visited
                    # Where possible, we try to generate a multi tile (4 tiles
                    # stored as one); otherwise, bordering tiles that are
                    # visited will all be single tiles.
                    l = [
                        (i, j) for i in range(0, width, 2)
                        for j in range(0, height, 2)
                    ]
                    if width % 2 == 1:
                        l.extend([(width-1, j) for j in range(1, height, 2)])
                    if height % 2 == 1:
                        l.extend([(i, height-1) for i in range(1, width, 2)])

                    # Generate the new reduced tileset
                    for i, j in l:
                        want_multi = i < width - 1 and j < height - 1
                        # Put the tile in the new tileset
                        o_tile = arrangement[x + i, y + j].tile
                        for n_tile in unused_tiles:
                            if want_multi:
                                n_tile_r = self.add_to_tile_index(n_tile, 1, 0)
                                n_tile_d = self.add_to_tile_index(n_tile, 0, 1)
                                n_tile_dr = self.add_to_tile_index(n_tile, 1, 1)
                                n_tiles = {n_tile, n_tile_r, n_tile_d, n_tile_dr}
                                if n_tiles.issubset(unused_tiles):
                                    unused_tiles.difference_update(n_tiles)
                                    break
                            else:
                                unused_tiles.remove(n_tile)
                                break
                        self.chars_tileset.tiles[n_tile] = tileset[o_tile]

                        entry = TitleScreenLayoutEntry(
                            i*8 + x_offset, j*8 + y_offset, n_tile, 0, unknown
                        )

                        # Create a multi entry if possible to save space
                        if want_multi:
                            entry.set_single(True)
                            o_tile_r = arrangement[x+i+1, y+j].tile
                            o_tile_d = arrangement[x+i, y+j+1].tile
                            o_tile_dr = arrangement[x+i+1, y+j+1].tile
                            self.chars_tileset.tiles[n_tile_r] = \
                                tileset[o_tile_r]
                            self.chars_tileset.tiles[n_tile_d] = \
                                tileset[o_tile_d]
                            self.chars_tileset.tiles[n_tile_dr] = \
                                tileset[o_tile_dr]

                        self.chars_layouts[c].append(entry)
                    self.chars_layouts[c][-1].set_final(True)

            elif original_tileset != tileset:
                log.warn(
                    "Tileset from characters frame {} does not match "
                    "tileset from characters frame 0.".format(p)
                )

    def write_to_project(self, resource_open):
        self.write_background_data_to_project(resource_open)
        self.write_chars_data_to_project(resource_open)

    def write_background_data_to_project(self, resource_open):
        # Write out BG1's animated frames
        for frame in range(NUM_ANIM_FRAMES):
            palette = EbPalette(7, BG_SUBPALETTE_LENGTH)
            for row in range(7):
                palette[row, :] = self.bg1_anim_palette[frame, row*16:(row+1)*16]
            with resource_open(BG1_FRAMES_PATH.format(frame), "png") as f:
                image = self.bg1_arrangement.image(self.bg1_tileset, palette)
                image.save(f)

        # Write out BG1's animated frames
        for frame in range(NUM_ANIM_FRAMES):
            with resource_open(BG2_FRAMES_PATH.format(frame), "png") as f:
                image = self.bg2_arrangement.image(self.bg2_tileset, self.bg2_anim_palette.get_subpalette(frame))
                image.save(f)

    def write_chars_data_to_project(self, resource_open):
        # Build an arrangement combining every character for convenience
        chars_positions = {}
        char_widths = [4, 6, 3, 3, 3, 3, 7]
        arrangement = EbTileArrangement(sum(char_widths), 6)
        for y in range(arrangement.height):
            for x in range(arrangement.width):
                arrangement[x, y].tile = CHARS_NUM_TILES - 1
        cur_tile_xpos = 0
        for c, layout in enumerate(self.chars_layouts):
            cur_char_width = char_widths[c]
            top_left = {'x': 128, 'y': 128}
            bottom_right = {'x': -128, 'y': -128}
            def _update_bounds(x, y):
                top_left['x'] = min(top_left['x'], x)
                top_left['y'] = min(top_left['y'], y)
                bottom_right['x'] = max(bottom_right['x'], x+8)
                bottom_right['y'] = max(bottom_right['y'], y+8)
            for entry in layout:
                tile = entry.tile & (CHARS_NUM_TILES - 1)
                _update_bounds(entry.x, entry.y)
                x = cur_tile_xpos + (entry.x) // 8     # Removed +16
                y = (entry.y) // 8                     # Removed +24
                arrangement[x, y].tile = tile
                if not entry.is_single():
                    arrangement[x+1, y].tile = tile + 1
                    arrangement[x, y+1].tile = tile + 16
                    arrangement[x+1, y+1].tile = tile + 17
                    _update_bounds(entry.x+8, entry.y+8)
            chars_positions[c] = {
                'x': cur_tile_xpos*8,
                'y': 0,
                'width': bottom_right['x']-top_left['x'],
                'height': bottom_right['y']-top_left['y'],
                'top_left_offset': top_left,
                'unknown': layout[0].unknown
            }
            cur_tile_xpos += cur_char_width

        # Write the characters animation frames
        for p in range(NUM_ANIM_FRAMES):
            with resource_open(CHARS_FRAMES_PATH.format(p), "png") as f:
                palette = EbPalette(8, BG_SUBPALETTE_LENGTH)
                for row in range(8):
                    palette[row, :] = self.chars_anim_palette[p, row*16:(row+1)*16]
                image = arrangement.image(
                    self.chars_tileset,
                    self.chars_anim_palette.get_subpalette(p)
                )
                image.save(f)

        # Write out the positions of the characters
        with resource_open(CHARS_POSITIONS_PATH, "yml", True) as f:
            yml_dump(chars_positions, f, False)

    def upgrade_project(
            self, old_version, new_version, rom, resource_open_r,
            resource_open_w, resource_delete):
        if old_version < 9:
            self.read_from_rom(rom)
            self.write_to_project(resource_open_w)

    @staticmethod
    def _decompress_block(rom, block, pointer: PointerReference):
        pointer_address = pointer.read(rom)
        block.from_compressed_block(
            block=rom,
            offset=from_snes_address(pointer_address)
        )

    @staticmethod
    def _write_compressed_block(rom, compressed_block, pointer: PointerReference):
        compressed_block.compress()
        new_offset = rom.allocate(data=compressed_block)
        pointer.write(rom, to_snes_address(new_offset))
        return new_offset
