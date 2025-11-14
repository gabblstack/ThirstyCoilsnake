import logging

from PIL import Image

from coilsnake.model.eb.fonts import EbFont, EbCreditsFont, EB_IMAGE_PALETTE, M2_DOSEI_IMAGE_PALETTE, M2_FLYOVER_IMAGE_PALETTE
from coilsnake.modules.eb.EbModule import EbModule
from coilsnake.model.eb.table import eb_table_from_offset
from coilsnake.util.common.image import open_indexed_image
from coilsnake.util.common.yml import yml_load, yml_dump
from coilsnake.util.eb.pointer import from_snes_address, to_snes_address, AsmPointerReference, XlPointerReference


log = logging.getLogger(__name__)

FONT_POINTER_TABLE_OFFSET = 0xC3EAED
FONT_FILENAMES = ["0", "1", "3", "4", "2"]

CREDITS_GRAPHICS_ASM_POINTER = 0x4C1E1 #$C4f1a7
CREDITS_PALETTES_ADDRESS = 0x21D6A6 #0x21e914

FLYOVER_POINTER_BANK = 0x41B28
FLYOVER_POINTER_LO16 = 0x41B62

DOSEI_GRAPHICS_ASM_POINTER = AsmPointerReference(0x1BF2D)
DOSEI_WIDTHS_ASM_POINTER = XlPointerReference(0x1BF1E)

SMALL_GRAPHICS_ASM_POINTER = AsmPointerReference(0x202C1)

class FontModule(EbModule):
    NAME = "Fonts"
    FREE_RANGES = [
        (0x21D2CC, 0x21D6A5),  # Credits font graphics - 0x21e528, 0x21e913
        # These don't exist in M2
        # (0x20110E, 0x201F0D),  # Fonts 0, 2, 3, and 4 - 0x210c7a, 0x212ef9
        (0x20110E, 0x201F0D),  # Small font for menu titles
        (0x20209D, 0x20309C),  # Font 1 - 0x201359, 0x201fb8
        (0x210000, 0x211601),  # Flyover font
    ]

    def __init__(self):
        super(FontModule, self).__init__()
        self.dosei_font = EbFont(num_characters=64, orig_characters=62, tile_width=8, tile_height=8,
                                 char_tile_ratio=2, bpp=2, clear_color=3, palette=M2_DOSEI_IMAGE_PALETTE)
        self.flyover_font = EbFont(num_characters=512, orig_characters=313, tile_width=12, tile_height=12,
                                   clear_color=0, palette=M2_FLYOVER_IMAGE_PALETTE)
        self.small_font = EbFont(num_characters=224, orig_characters=224, tile_width=8, tile_height=8,
                                 bpp=2, clear_color=3, palette=M2_DOSEI_IMAGE_PALETTE)
        self.credits_font = EbCreditsFont()

    def read_from_rom(self, rom):
        flyover_offset = from_snes_address(rom[FLYOVER_POINTER_BANK] << 16 | rom.read_multi(FLYOVER_POINTER_LO16, 2))
        self.flyover_font.from_block(rom, flyover_offset, None)

        dosei_graphics_offset = from_snes_address(DOSEI_GRAPHICS_ASM_POINTER.read(rom))
        dosei_widths_offset = from_snes_address(DOSEI_WIDTHS_ASM_POINTER.read(rom))
        self.dosei_font.from_block(rom, dosei_graphics_offset, dosei_widths_offset)

        small_offset = from_snes_address(SMALL_GRAPHICS_ASM_POINTER.read(rom))
        self.small_font.from_block(rom, small_offset, None)

        self.read_credits_font_from_rom(rom)

    def write_to_rom(self, rom):
        flyover_offset, _ = self.flyover_font.to_block(rom)
        flyover_pointer = to_snes_address(flyover_offset)
        rom[FLYOVER_POINTER_BANK] = flyover_pointer >> 16
        rom.write_multi(FLYOVER_POINTER_LO16, flyover_pointer & 0xFFFF, 2)

        dosei_graphics_offset, dosei_widths_offset = self.dosei_font.to_block(rom)
        DOSEI_GRAPHICS_ASM_POINTER.write(rom, to_snes_address(dosei_graphics_offset))
        DOSEI_WIDTHS_ASM_POINTER.write(rom, to_snes_address(dosei_widths_offset))

        small_offset, _ = self.small_font.to_block(rom)
        SMALL_GRAPHICS_ASM_POINTER.write(rom, to_snes_address(small_offset))

        self.write_credits_font_to_rom(rom)

    def read_from_project(self, resource_open):
        with resource_open("Fonts/flyover", 'png') as image_file:
            self.flyover_font.from_files(image_file, None)

        with resource_open("Fonts/dosei", 'png') as image_file:
            with resource_open("Fonts/dosei_widths", 'yml', True) as widths_file:
                self.dosei_font.from_files(image_file, widths_file)

        with resource_open("Fonts/small", 'png') as image_file:
            self.small_font.from_files(image_file, None)

        self.read_credits_font_from_project(resource_open)

    def write_to_project(self, resource_open):
        with resource_open("Fonts/flyover", 'png') as image_file:
            self.flyover_font.to_files(image_file, None)
            
        with resource_open("Fonts/dosei", 'png') as image_file:
            with resource_open("Fonts/dosei_widths", 'yml', True) as widths_file:
                self.dosei_font.to_files(image_file, widths_file)

        with resource_open("Fonts/small", 'png') as image_file:
            self.small_font.to_files(image_file, None)

        self.write_credits_font_to_project(resource_open)

    def read_credits_font_from_rom(self, rom):
        log.debug("Reading the credits font from the ROM")
        self.credits_font.from_block(block=rom,
                                     tileset_asm_pointer_offset=CREDITS_GRAPHICS_ASM_POINTER,
                                     palette_offset=CREDITS_PALETTES_ADDRESS)

    def write_credits_font_to_rom(self, rom):
        log.debug("Writing the credits font to the ROM")
        self.credits_font.to_block(block=rom,
                                   tileset_asm_pointer_offset=CREDITS_GRAPHICS_ASM_POINTER,
                                   palette_offset=CREDITS_PALETTES_ADDRESS)

    def write_credits_font_to_project(self, resource_open):
        with resource_open("Fonts/credits", "png") as image_file:
            self.credits_font.to_files(image_file, "png")

    def read_credits_font_from_project(self, resource_open):
        with resource_open("Fonts/credits", "png") as image_file:
            self.credits_font.from_files(image_file, "png")

    def upgrade_project(self, old_version, new_version, rom, resource_open_r, resource_open_w, resource_delete):
        if old_version == new_version:
            return
        elif old_version == 5:
            # Expand all the fonts from 96 characters to 128 characters
            for i, font in enumerate(self.fonts):
                log.debug("Expanding font #{}".format(FONT_FILENAMES[i]))
                image_resource_name = "Fonts/" + FONT_FILENAMES[i]
                widths_resource_name = "Fonts/" + FONT_FILENAMES[i] + "_widths"
                new_image_w, new_image_h = font.image_size()

                # Expand the image

                with resource_open_r(image_resource_name, 'png') as image_file:
                    image = open_indexed_image(image_file)

                    expanded_image = Image.new("P", (new_image_w, new_image_h), None)
                    for y in range(new_image_h):
                        for x in range(new_image_w):
                            expanded_image.putpixel((x, y), 1)
                    EB_IMAGE_PALETTE.to_image(expanded_image)
                    expanded_image.paste(image, (0, 0))

                    with resource_open_w(image_resource_name, 'png') as image_file2:
                        expanded_image.save(image_file2, "png")

                # Expand the widths

                with resource_open_r(widths_resource_name, "yml", True) as widths_file:
                    widths_dict = yml_load(widths_file)

                for character_id in range(96, 128):
                    if character_id not in widths_dict:
                        widths_dict[character_id] = 0

                with resource_open_w(widths_resource_name, "yml", True) as widths_file:
                    yml_dump(widths_dict, widths_file, default_flow_style=False)

            self.upgrade_project(6, new_version, rom, resource_open_r, resource_open_w, resource_delete)
        elif old_version <= 2:
            # The credits font was a new feature in version 3

            self.read_credits_font_from_rom(rom)
            self.write_credits_font_to_project(resource_open_w)
            self.upgrade_project(3, new_version, rom, resource_open_r, resource_open_w, resource_delete)
        else:
            self.upgrade_project(old_version + 1, new_version, rom, resource_open_r, resource_open_w, resource_delete)
