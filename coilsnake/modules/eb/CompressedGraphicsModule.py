from collections import namedtuple
import logging

from coilsnake.model.eb.graphics import EbTileArrangement, EbTownMap, EbCompanyLogo, EbAttractModeLogo, \
    EbGasStationLogo, EbTownMapIcons
from coilsnake.model.eb.town_maps import TOWN_MAP_NAMES
from coilsnake.modules.eb.EbModule import EbModule
from coilsnake.util.common.image import open_indexed_image, open_image
from coilsnake.util.eb.pointer import from_snes_address, to_snes_address, read_asm_pointer, write_asm_pointer


log = logging.getLogger(__name__)


TOWN_MAP_RESOURCE_NAMES = ["TownMaps/" + x for x in TOWN_MAP_NAMES]
TOWN_MAP_POINTER_OFFSETS = range(0x2030E5, 0x2030E5 + 6 * 4, 4)

TOWN_MAP_ICON_GRAPHICS_ASM_POINTER_OFFSET = 0x4A8FF #$4d62f
TOWN_MAP_ICON_PALETTE_ASM_POINTER_OFFSET = 0x4A894 #$4d5c4

EbCompressedGraphicInfo = namedtuple("EbCompressedGraphicInfo",
                                     ["name",
                                      "graphics_asm_pointer_offsets",
                                      "arrangement_asm_pointer_offsets",
                                      "palette_asm_pointer_offsets"])

COMPANY_LOGO_INFOS = [EbCompressedGraphicInfo(name="Logos/Nintendo",
                                              graphics_asm_pointer_offsets=[0xEF6C], #$C0/EEA3
                                              arrangement_asm_pointer_offsets=[0xEF84], #$C0/EEBB
                                              palette_asm_pointer_offsets=[0xEF9C]), #$C0/EED3
                      EbCompressedGraphicInfo(name="Logos/APE",
                                              graphics_asm_pointer_offsets=[0xEFC4], #$C0/EEFB
                                              arrangement_asm_pointer_offsets=[0xEFDC], #$C0/EF13
                                              palette_asm_pointer_offsets=[0xEFF4]), #$C0/EF2B
                      EbCompressedGraphicInfo(name="Logos/HALKEN",
                                              graphics_asm_pointer_offsets=[0xF01B], #$C0/EF52
                                              arrangement_asm_pointer_offsets=[0xF033], #$C0/EF6A
                                              palette_asm_pointer_offsets=[0xF04B])] #$C0/EF82

ATTRACT_MODE_INFOS = [EbCompressedGraphicInfo(name="Logos/ProducedBy",
                                              graphics_asm_pointer_offsets=[0x4AF84], #$C/4DD73
                                              arrangement_asm_pointer_offsets=[0x4AF4B], #$C/4DD3A
                                              palette_asm_pointer_offsets=[0x4AFB0]), #$C/4DD9F
                      EbCompressedGraphicInfo(name="Logos/PresentedBy",
                                              graphics_asm_pointer_offsets=[0x4B02C], #$C/4DE1B
                                              arrangement_asm_pointer_offsets=[0x4AFF3], #$C/4DDE2
                                              palette_asm_pointer_offsets=[0x4B058])] #$C/4DE47

GAS_STATION_INFO = EbCompressedGraphicInfo(name="Logos/GasStation",
                                           graphics_asm_pointer_offsets=[0xF1B9], #$C0/F0F0
                                           arrangement_asm_pointer_offsets=[0xF1E4], #$C0/F11B
                                           palette_asm_pointer_offsets=[0xF210, 0xF489, 0xF4BF]) #$F147, $F3BA, $F3F0

TOWN_MAP_ICON_PREVIEW_SUBPALETTES = [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1,

    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,

    0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0,
    0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0,
    0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0,

    1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,

    0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,

    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
TOWN_MAP_ICON_PREVIEW_ARRANGEMENT = EbTileArrangement(width=16, height=18)
for i in range(16 * 18):
    item = TOWN_MAP_ICON_PREVIEW_ARRANGEMENT[i % 16, i // 16]
    item.is_priority = False
    item.is_horizontally_flipped = False
    item.is_vertically_flipped = False
    item.subpalette = TOWN_MAP_ICON_PREVIEW_SUBPALETTES[i]
    item.tile = i


class CompressedGraphicsModule(EbModule):
    NAME = "Compressed Graphics"
    FREE_RANGES = [(0x2030FD, 0x20FC87),  # Town Map data - 0x2021a8, 0x20ed02
                   (0x214317, 0x219DE0),  # Company Logos, "Produced by" and "Presented by", and Gas Station - 0x214ec1, 0x21ae7b
                   (0x21D7E2, 0x21DF3D)]  # Town map icon graphics and palette - 0x21ea50, 0x21f203

    def __init__(self):
        super(CompressedGraphicsModule, self).__init__()
        self.town_maps = [EbTownMap() for x in TOWN_MAP_POINTER_OFFSETS]
        self.town_map_icons = EbTownMapIcons()
        self.company_logos = [EbCompanyLogo() for x in COMPANY_LOGO_INFOS]
        self.attract_mode_logos = [EbAttractModeLogo() for x in ATTRACT_MODE_INFOS]
        self.gas_station_logo = EbGasStationLogo()

    def __exit__(self, type, value, traceback):
        del self.town_maps
        del self.town_map_icons
        del self.company_logos
        del self.attract_mode_logos
        del self.gas_station_logo

    def read_from_rom(self, rom):
        self.read_town_maps_from_rom(rom)
        self.read_town_map_icons_from_rom(rom)
        self.read_company_logos_from_rom(rom)
        self.read_attract_mode_logos_from_rom(rom)
        self.read_gas_station_from_rom(rom)

    def write_to_rom(self, rom):
        self.write_town_maps_to_rom(rom)
        self.write_town_map_icons_to_rom(rom)
        self.write_company_logos_to_rom(rom)
        self.write_attract_mode_logos_to_rom(rom)
        self.write_gas_station_to_rom(rom)

    def read_town_maps_from_rom(self, rom):
        log.debug("Reading town maps")
        for pointer_offset, town_map in zip(TOWN_MAP_POINTER_OFFSETS, self.town_maps):
            offset = from_snes_address(rom.read_multi(pointer_offset, size=4))
            town_map.from_block(block=rom,
                                offset=offset)

    def write_town_maps_to_rom(self, rom):
        log.debug("Writing town maps")
        for pointer_offset, town_map in zip(TOWN_MAP_POINTER_OFFSETS, self.town_maps):
            offset = town_map.to_block(rom)
            rom.write_multi(pointer_offset, to_snes_address(offset), size=4)

    def read_town_map_icons_from_rom(self, rom):
        log.debug("Reading town map icons")
        graphics_offset = from_snes_address(read_asm_pointer(block=rom,
                                                             offset=TOWN_MAP_ICON_GRAPHICS_ASM_POINTER_OFFSET))
        palette_offset = from_snes_address(read_asm_pointer(block=rom,
                                                            offset=TOWN_MAP_ICON_PALETTE_ASM_POINTER_OFFSET))
        self.town_map_icons.from_block(block=rom,
                                       graphics_offset=graphics_offset,
                                       arrangement_offset=0,
                                       palette_offsets=[palette_offset])

    def write_town_map_icons_to_rom(self, rom):
        log.debug("Writing town map icons")
        graphics_offset, arrangement_offset, palette_offsets = self.town_map_icons.to_block(rom)
        write_asm_pointer(block=rom,
                          offset=TOWN_MAP_ICON_GRAPHICS_ASM_POINTER_OFFSET,
                          pointer=to_snes_address(graphics_offset))
        write_asm_pointer(block=rom,
                          offset=TOWN_MAP_ICON_PALETTE_ASM_POINTER_OFFSET,
                          pointer=to_snes_address(palette_offsets[0]))

    def read_company_logos_from_rom(self, rom):
        log.debug("Reading company logos")
        self.read_logos_from_rom(rom, self.company_logos, COMPANY_LOGO_INFOS)

    def write_company_logos_to_rom(self, rom):
        log.debug("Writing company logos")
        self.write_logos_to_rom(rom, self.company_logos, COMPANY_LOGO_INFOS)

    def read_attract_mode_logos_from_rom(self, rom):
        log.debug("Reading attract mode logos")
        self.read_logos_from_rom(rom, self.attract_mode_logos, ATTRACT_MODE_INFOS)

    def write_attract_mode_logos_to_rom(self, rom):
        log.debug("Writing attract mode logos")
        self.write_logos_to_rom(rom, self.attract_mode_logos, ATTRACT_MODE_INFOS)

    def read_gas_station_from_rom(self, rom):
        log.debug("Reading gas station logo")
        self.read_logos_from_rom(rom, [self.gas_station_logo], [GAS_STATION_INFO])

    def write_gas_station_to_rom(self, rom):
        log.debug("Writing gas station logo")
        self.write_logos_to_rom(rom, [self.gas_station_logo], [GAS_STATION_INFO])

    def read_logos_from_rom(self, rom, logos, infos):
        for info, logo in zip(infos, logos):
            graphics_offset = from_snes_address(read_asm_pointer(rom, info.graphics_asm_pointer_offsets[0]))
            arrangement_offset = from_snes_address(read_asm_pointer(rom, info.arrangement_asm_pointer_offsets[0]))
            palette_offsets = [from_snes_address(read_asm_pointer(rom, x)) for x in info.palette_asm_pointer_offsets]

            logo.from_block(block=rom,
                            graphics_offset=graphics_offset,
                            arrangement_offset=arrangement_offset,
                            palette_offsets=palette_offsets)

    def write_logos_to_rom(self, rom, logos, infos):
        for info, logo in zip(infos, logos):
            graphics_offset, arrangement_offset, palette_offsets = logo.to_block(rom)

            for asm_pointer_offset in info.graphics_asm_pointer_offsets:
                write_asm_pointer(block=rom, offset=asm_pointer_offset, pointer=to_snes_address(graphics_offset))
            for asm_pointer_offset in info.arrangement_asm_pointer_offsets:
                write_asm_pointer(block=rom, offset=asm_pointer_offset, pointer=to_snes_address(arrangement_offset))
            for offset, asm_pointer_offset in zip(palette_offsets, info.palette_asm_pointer_offsets):
                write_asm_pointer(block=rom, offset=asm_pointer_offset, pointer=to_snes_address(offset))

    def read_from_project(self, resource_open):
        self.read_town_maps_from_project(resource_open)
        self.read_town_map_icons_from_project(resource_open)
        self.read_company_logos_from_project(resource_open)
        self.read_attract_mode_logos_from_project(resource_open)
        self.read_gas_station_from_project(resource_open)

    def write_to_project(self, resource_open):
        self.write_town_maps_to_project(resource_open)
        self.write_town_map_icons_to_project(resource_open)
        self.write_company_logos_to_project(resource_open)
        self.write_attract_mode_logos_to_project(resource_open)
        self.write_gas_station_to_project(resource_open)

    def read_town_maps_from_project(self, resource_open):
        for resource_name, town_map in zip(TOWN_MAP_RESOURCE_NAMES, self.town_maps):
            log.info("- Reading {}".format(resource_name))
            with resource_open(resource_name, "png") as image_file:
                image = open_indexed_image(image_file)
                town_map.from_image(image)

    def write_town_maps_to_project(self, resource_open):
        log.debug("Writing town maps")
        for resource_name, town_map in zip(TOWN_MAP_RESOURCE_NAMES, self.town_maps):
            image = town_map.image()
            with resource_open(resource_name, "png") as image_file:
                image.save(image_file, "png")

    def read_town_map_icons_from_project(self, resource_open):
        log.info("- Reading town map icons")
        with resource_open("TownMaps/icons", "png") as image_file:
            image = open_indexed_image(image_file)
            self.town_map_icons.from_image(image=image, arrangement=TOWN_MAP_ICON_PREVIEW_ARRANGEMENT)

    def write_town_map_icons_to_project(self, resource_open):
        log.debug("Writing town map icons")
        image = self.town_map_icons.image(TOWN_MAP_ICON_PREVIEW_ARRANGEMENT)
        with resource_open("TownMaps/icons", "png") as image_file:
            image.save(image_file, "png")

    def read_company_logos_from_project(self, resource_open):
        self.read_logos_from_project(resource_open, self.company_logos, COMPANY_LOGO_INFOS)

    def write_company_logos_to_project(self, resource_open):
        log.debug("Writing company logos")
        self.write_logos_to_project(resource_open, self.company_logos, COMPANY_LOGO_INFOS)

    def read_attract_mode_logos_from_project(self, resource_open):
        self.read_logos_from_project(resource_open, self.attract_mode_logos, ATTRACT_MODE_INFOS)

    def write_attract_mode_logos_to_project(self, resource_open):
        log.debug("Writing attract mode logos")
        self.write_logos_to_project(resource_open, self.attract_mode_logos, ATTRACT_MODE_INFOS)

    def read_logos_from_project(self, resource_open, logos, infos):
        for info, logo in zip(infos, logos):
            log.info("- Reading " + info.name)
            with resource_open(info.name, "png") as image_file:
                image = open_indexed_image(image_file)
                logo.from_image(image)

    def write_logos_to_project(self, resource_open, logos, infos):
        for info, logo in zip(infos, logos):
            image = logo.image()
            with resource_open(info.name, "png") as image_file:
                image.save(image_file, "png")

    def read_gas_station_from_project(self, resource_open):
        log.info("- Reading gas station logo")
        with resource_open(GAS_STATION_INFO.name + "1", "png") as image1_file:
            image1 = open_image(image1_file)
            with resource_open(GAS_STATION_INFO.name + "2", "png") as image2_file:
                image2 = open_image(image2_file)
                with resource_open(GAS_STATION_INFO.name + "3", "png") as image3_file:
                    image3 = open_image(image3_file)
                    self.gas_station_logo.from_images([image1, image2, image3])

    def write_gas_station_to_project(self, resource_open):
        log.debug("Writing gas station logo")
        images = self.gas_station_logo.images()
        with resource_open(GAS_STATION_INFO.name + "1", "png") as image_file:
            images[0].save(image_file, "png")
        with resource_open(GAS_STATION_INFO.name + "2", "png") as image_file:
            images[1].save(image_file, "png")
        with resource_open(GAS_STATION_INFO.name + "3", "png") as image_file:
            images[2].save(image_file, "png")

    def upgrade_project(self, old_version, new_version, rom, resource_open_r, resource_open_w, resource_delete):
        if old_version == new_version:
            return
        elif old_version <= 2:
            self.read_town_map_icons_from_rom(rom)
            self.write_town_map_icons_to_project(resource_open_w)

            self.read_attract_mode_logos_from_rom(rom)
            self.write_attract_mode_logos_to_project(resource_open_w)

            self.read_gas_station_from_rom(rom)
            self.write_gas_station_to_project(resource_open_w)

            self.upgrade_project(3, new_version, rom, resource_open_r, resource_open_w, resource_delete)
        else:
            self.upgrade_project(old_version + 1, new_version, rom, resource_open_r, resource_open_w, resource_delete)
