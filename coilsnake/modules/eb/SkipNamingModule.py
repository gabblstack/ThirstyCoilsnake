import logging
from coilsnake.modules.eb.EbModule import EbModule
from coilsnake.util.common.yml import yml_load, yml_dump
from coilsnake.util.eb.pointer import to_snes_address
from coilsnake.util.eb.text import standard_text_to_byte_list
from coilsnake.exceptions.common.exceptions import CoilSnakeUserError

log = logging.getLogger(__name__)

class SkipNamingModule(EbModule):
    NAME = "Skip Names"

    def write_to_project(self, resource_open):
        out = {"Enable Skip": False,
               "Enable Summary": False,
               "Name1": "ネス", #Nesu (Ness)
               "Name2": "ポーラ", #Paula
               "Name3": "ジェフ", #Jeff
               "Name4": "プー", #Pū (Poo)
               "Pet": "チビ", #Chibi (King)
               "Food": "ハンバーグ", #Salisbury steak (Steak)
               "Thing": "キアイ"} #Kiai (Rockin)
        with resource_open("naming_skip", "yml", True) as f:
            yml_dump(out, f, default_flow_style=False)

    def read_from_project(self, resource_open):
        with resource_open("naming_skip", "yml", True) as f:
            self.data = yml_load(f)

    def write_loader_asm(self, rom, offset, s, strlen, mem_offset, byte2):
        i = 0
        byte_list = standard_text_to_byte_list(s, strlen, False)
        for byte in byte_list:
            rom[offset:offset+5] = [0xa9, byte, 0x8d, mem_offset + i, byte2]
            i += 1
            offset += 5
        return offset

    def write_to_rom(self, rom):
        if self.data["Enable Skip"]:
            # this fixes the naming screen music playing briefly when skip naming is on
            # it works by changing the jump from @CHANGE_TO_NAMING_SCREEN_MUSIC to @UNKNOWN18 (which normally runs directly after the music change)
            # https://github.com/Herringway/ebsrc/blob/87f514cb4b77fa3193bcb122ea51f5de5cfdd9cf/src/intro/file_select_menu_loop.asm#L101
            # Verify the code structure first:
            if rom[0x1F752] == 0xF0 and rom[0x1F753] == 0xE5: #$c/1f8f0 - $c/1f8f1
                rom[0x1F754] = 0x80
                rom[0x1F755] = 0x05
            else:
                log.warn("Unable to apply naming screen music bypass due to existing ASM changes")

            offset = rom.allocate(size=(10 + 4 * 4 * 5 + 3 * 6 * 5))
            # Patch ASM to "JML newCode"
            if bytes(rom.to_array()[0x1F8FA:0x1F8FE]) != b'\xa9\x07\x00\x18': #$c/1faae - $c/1fab2
                raise CoilSnakeUserError("Naming ASM has already been patched - unable to apply naming skip")
            rom[0x1F8FA] = 0x5c
            rom.write_multi(0x1F8FB, to_snes_address(offset), 3) #$c/1faaf
            rom[offset:offset+4] = [0x48, 0x08, 0xe2, 0x20]
            offset += 4

            offset = self.write_loader_asm(rom, offset, self.data["Name1"], 4, 0x7f, 0x9c) #0xce, 0x99
            offset = self.write_loader_asm(rom, offset, self.data["Name2"], 4, 0xdd, 0x9c) #0x2d, 0x9a
            offset = self.write_loader_asm(rom, offset, self.data["Name3"], 4, 0x3b, 0x9d) #0x8c, 0x9a
            offset = self.write_loader_asm(rom, offset, self.data["Name4"], 4, 0x99, 0x9d) #0xeb, 0x9a
            offset = self.write_loader_asm(rom, offset, self.data["Pet"],   6, 0xcd, 0x9a) #0x19, 0x98
            offset = self.write_loader_asm(rom, offset, self.data["Food"],  6, 0xd3, 0x9a) #0x1f, 0x98
            offset = self.write_loader_asm(rom, offset, self.data["Thing"], 6, 0xdb, 0x9a) #0x29, 0x98

            if self.data["Enable Summary"]:
                rom[offset:offset+6] = [0x28, 0x68, 0x5c, 0x0c, 0xf9, 0xc1] #0xc0, 0xfa, 0xc1
            else:
                rom[offset:offset+6] = [0x28, 0x68, 0x5c, 0xb3, 0xfa, 0xc1] #0x05, 0xfd, 0xc1
