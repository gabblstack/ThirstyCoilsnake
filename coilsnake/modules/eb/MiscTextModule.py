from coilsnake.model.eb.table import EbStandardNullTerminatedTextTableEntry, EbStandardTextTableEntry
from coilsnake.modules.eb.EbModule import EbModule
from coilsnake.util.common.yml import yml_load, yml_dump
from coilsnake.util.eb.pointer import read_asm_pointer, from_snes_address, write_asm_pointer, to_snes_address

class EbMiscTextAsmPointer(object):
    def __init__(self, asm_pointer_loc):
        self.asm_pointer_loc = asm_pointer_loc

    def read(self, block):
        return from_snes_address(read_asm_pointer(block, self.asm_pointer_loc))

    def write(self, block, address):
        write_asm_pointer(block=block, offset=self.asm_pointer_loc, pointer=address)


class EbMiscTextString(object):
    def __init__(self, pointers=None, default_offset=None, maximum_size=None, null_terminated=False):
        if pointers and default_offset:
            raise ValueError("Only one of pointers and default_offset can be provided to EbStandardMiscText")
        if not maximum_size:
            raise ValueError("maximum_size must be provided")

        self.pointers = pointers
        self.default_offset = default_offset
        if null_terminated:
            self.table_entry = EbStandardNullTerminatedTextTableEntry.create(maximum_size)
        else:
            self.table_entry = EbStandardTextTableEntry.create(maximum_size)

    def from_block(self, block):
        if self.pointers:
            loc = self.pointers[0].read(block)
        else:
            loc = self.default_offset

        return self.table_entry.from_block(block, loc)

    def to_block(self, block, value):
        if self.pointers:
            loc = block.allocate(size=self.table_entry.size)

            for pointer in self.pointers:
                pointer.write(block, to_snes_address(loc))
        else:
            loc = self.default_offset

        value = self.table_entry.from_yml_rep(value)
        self.table_entry.to_block(block, loc, value)

MISC_TEXT = {
    "Starting Text": {
        "Start New Game": EbMiscTextString(default_offset=0x00494A3, maximum_size=10),                                                #C4c060
        "Text Speed": EbMiscTextString(default_offset=0x0494A8, maximum_size=4),                                                      #C4c074
        "Text Speed Fast": EbMiscTextString(default_offset=0x0494AE, maximum_size=4),                                                 #C4c07f
        "Text Speed Medium": EbMiscTextString(default_offset=0x0494B2, maximum_size=4),                                               #C4c086
        "Text Speed Slow": EbMiscTextString(default_offset=0x0494B6, maximum_size=4),                                                 #C4c08d
        "Continue": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x1EF91)], maximum_size=4),                                       #C1F08C
        "Copy": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x1EFCA)], maximum_size=4),                                           #C1F0C5 
        "Delete": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x1F007)], maximum_size=3),                                         #C1F102
        "Set Up": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x1F025)], maximum_size=5),                                         #C1F120
        "Copy to where?": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x1F087), EbMiscTextAsmPointer(0x1F105)], maximum_size=11), #C1F189 - C1F208
        "Confirm Delete": EbMiscTextString(default_offset=0x0494D5, maximum_size=13),                                                 #C4c0be
        "Confirm Delete No": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x1F238)], maximum_size=5),                              #C1F364
        "Confirm Delete Yes": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x1F254)], maximum_size=3),                             #C1F380
        "Select Speed": EbMiscTextString(default_offset=0x0494EA, maximum_size=9),                                                    #C4c0e5
        "Select Sound": EbMiscTextString(default_offset=0x0494F3, maximum_size=6),                                                    #C4c0fe
        "Select Sound Stereo": EbMiscTextString(default_offset=0x0494F9, maximum_size=5),                                             #C4c11a
        "Select Sound Mono": EbMiscTextString(default_offset=0x0494FE, maximum_size=5),                                               #C4c121
        "Select Style": EbMiscTextString(default_offset=0x049503, maximum_size=10),                                                   #C4c128
        "Ask Name 1": EbMiscTextString(default_offset=0x049525, maximum_size=15),                                                     #C4c194
        "Ask Name 2": EbMiscTextString(default_offset=0x049534, maximum_size=15),                                                     #C4c1bc
        "Ask Name 3": EbMiscTextString(default_offset=0x049543, maximum_size=15),                                                     #C4c1e4
        "Ask Name 4": EbMiscTextString(default_offset=0x049552, maximum_size=15),                                                     #C4c20c
        "Ask Name Pet": EbMiscTextString(default_offset=0x049561, maximum_size=15),                                                   #C4c234
        "Ask Name Food": EbMiscTextString(default_offset=0x049570, maximum_size=15),                                                  #C4c25c
        "Ask Name PSI": EbMiscTextString(default_offset=0x04957F, maximum_size=15),                                                   #C4c284
        "Confirm Food": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x1F950)], maximum_size=9),                                   #C1FB05
        "Confirm PSI": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x1F9B8)], maximum_size=11),                                   #C1FBB7
        "Confirm All": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x1FA1D)], maximum_size=12),                                   #C1FC69
        "Confirm All Yes": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x1FA37)], maximum_size=3),                                #C1FC83
        "Confirm All No": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x1FA55)], maximum_size=4)                                  #C1FCA1
    },
    "Ailments": {
        "Ailment 01": EbMiscTextString(default_offset=0x043947, maximum_size=10), #C45b70
        "Ailment 02": EbMiscTextString(default_offset=0x043951, maximum_size=10), #C45b80
        "Ailment 03": EbMiscTextString(default_offset=0x04395B, maximum_size=10), #C45b90
        "Ailment 04": EbMiscTextString(default_offset=0x043965, maximum_size=10), #C45ba0
        "Ailment 05": EbMiscTextString(default_offset=0x04396F, maximum_size=10), #C45bb0
        "Ailment 06": EbMiscTextString(default_offset=0x043979, maximum_size=10), #C45bc0
        "Ailment 07": EbMiscTextString(default_offset=0x043983, maximum_size=10), #C45bd0
        "Ailment 08": EbMiscTextString(default_offset=0x04398D, maximum_size=10), #C45be0
        "Ailment 09": EbMiscTextString(default_offset=0x043997, maximum_size=10), #C45bf0
        "Ailment 10": EbMiscTextString(default_offset=0x0439A1, maximum_size=10)  #C45c00
    },
    "Battle Menu": {
        "Bash": EbMiscTextString(default_offset=0x0474B7, maximum_size=5),                                             #C49fe1
        "Goods": EbMiscTextString(default_offset=0x0474BC, maximum_size=5),                                            #C49ff1
        "Auto Fight": EbMiscTextString(default_offset=0x0474C1, maximum_size=5),                                       #C4a001
        "PSI": EbMiscTextString(default_offset=0x0474C6, maximum_size=5),                                              #C4a011
        "Defend": EbMiscTextString(default_offset=0x0474CB, maximum_size=5),                                           #C4a021
        "Pray": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x236CA)], maximum_size=5, null_terminated=True),      #C237E0
        "Shoot": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x2353B)], maximum_size=5, null_terminated=True),     #C23616
        "Spy": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x23671)], maximum_size=5, null_terminated=True),       #C2378B
        "Run Away": EbMiscTextString(default_offset=0x0474DF, maximum_size=5),                                         #C4a061
        "Mirror": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x236F2)], maximum_size=5, null_terminated=True),    #C23808
        "Do Nothing": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x2355C)], maximum_size=7, null_terminated=True) #C23637
    },
    "Out of Battle Menu": {
        "Talk to": EbMiscTextString(default_offset=0x9DD30, maximum_size=5),             #2fa37a
        "Goods": EbMiscTextString(default_offset=0x9DD35, maximum_size=5),               #2fa384
        "PSI": EbMiscTextString(default_offset=0x9DD3A, maximum_size=5),                 #2fa38e
        "Equip": EbMiscTextString(default_offset=0x9DD3F, maximum_size=5),               #2fa398
        "Check": EbMiscTextString(default_offset=0x9DD44, maximum_size=5),               #2fa3a2
        "Status": EbMiscTextString(default_offset=0x9DD49, maximum_size=5)               #2fa3ac
    },
    "Status Window": {
        "Level": EbMiscTextString(default_offset=0x9DD55, maximum_size=4),               #2fa3ba
        "Hit Points": EbMiscTextString(default_offset=0x9DD5D, maximum_size=11),         #2fa3c4
        "Psychic Points": EbMiscTextString(default_offset=0x9DD6D, maximum_size=11),     #2fa3d3
        "Experience Points": EbMiscTextString(default_offset=0x9DD7D, maximum_size=6),   #2fa3e6
        "Exp. for next level": EbMiscTextString(default_offset=0x9DD87, maximum_size=9), #2fa3fc
        "Offense": EbMiscTextString(default_offset=0x9DD94, maximum_size=6),             #2fa414
        "Defense": EbMiscTextString(default_offset=0x9DD9E, maximum_size=7),             #2fa420
        "Speed": EbMiscTextString(default_offset=0x9DDA9, maximum_size=5),               #2fa42c
        "Guts": EbMiscTextString(default_offset=0x9DDB2, maximum_size=4),                #2fa436
        "Vitality": EbMiscTextString(default_offset=0x9DDBA, maximum_size=7),            #2fa43f
        "IQ": EbMiscTextString(default_offset=0x9DDC5, maximum_size=3),                  #2fa44c
        "Luck": EbMiscTextString(default_offset=0x9DDCC, maximum_size=4),                #2fa453
        "PSI Prompt": EbMiscTextString(default_offset=0x04392C, maximum_size=27)         #C45b4d
    },
    "Other": {
        "Player Name Prompt": EbMiscTextString(default_offset=0x03F670, maximum_size=12), #C3fb2b
        "Lumine Hall Text": EbMiscTextString(default_offset=0x045CE6, maximum_size=100)   #C48037
    },
    "PSI Types": {
        "Offense": EbMiscTextString(default_offset=0x03EC1B, maximum_size=4), #C3f090
        "Recover": EbMiscTextString(default_offset=0x03EC20, maximum_size=4), #C3f098
        "Assist": EbMiscTextString(default_offset=0x03EC25, maximum_size=4),  #C3f0a0
        "Other": EbMiscTextString(default_offset=0x03EC2A, maximum_size=4)    #C3f0a8
    },
    "PSI Menu": {
        "PP Cost": EbMiscTextString(default_offset=0x03EC9B, maximum_size=8),                                        #C3f11c
        "To enemy": EbMiscTextString(default_offset=0x03ECA3, maximum_size=9),                                       #C3f124
        "To one enemy": EbMiscTextString(default_offset=0x03ECAC, maximum_size=9),                                   #C3f138
        "To one enemy 2": EbMiscTextString(default_offset=0x03ECB5, maximum_size=9),                                 #C3f14c
        "To row of foes": EbMiscTextString(default_offset=0x03ECBE, maximum_size=9),                                 #C3f160
        "To all enemies": EbMiscTextString(default_offset=0x03ECC7, maximum_size=9),                                 #C3f174
        "himself": EbMiscTextString(default_offset=0x03ECD0, maximum_size=9),                                        #C3f188
        "To one of us": EbMiscTextString(default_offset=0x03ECD9, maximum_size=9),                                   #C3f19c
        "To one of us 2": EbMiscTextString(default_offset=0x03ECE2, maximum_size=9),                                 #C3f1b0
        "To all of us": EbMiscTextString(default_offset=0x03ECEB, maximum_size=9),                                   #C3f1c4
        "To all of us 2": EbMiscTextString(default_offset=0x03ECF4, maximum_size=9),                                 #C3f1d8
        "Row To": EbMiscTextString(default_offset=0x0432F5, maximum_size=8),                                         #C454f2
        "Row Front": EbMiscTextString(default_offset=0x432FD, maximum_size=4),                                       #C454f5
        "Row Back": EbMiscTextString(default_offset=0x43301, maximum_size=4)                                         #C45502
    },
    "Equip Menu": {
        "Offense": EbMiscTextString(default_offset=0x0439B1, maximum_size=6),                                        #C45c1c
        "Defense": EbMiscTextString(default_offset=0x0439B7, maximum_size=7),                                        #C45c24
        # "Weapon": EbMiscTextString(default_offset=0x0, maximum_size=10),                                           #C45c2c
        # "Body": EbMiscTextString(default_offset=0x0, maximum_size=10),                                             #C45c37
        # "Arms": EbMiscTextString(default_offset=0x0, maximum_size=10),                                             #C45c42
        # "Other": EbMiscTextString(default_offset=0x0, maximum_size=10),                                            #C45c4d
        "Weapon Window Title": EbMiscTextString(default_offset=0x0439BE, maximum_size=4),                            #C45c58
        "Body Window Title": EbMiscTextString(default_offset=0x0439C2, maximum_size=4),                              #C45c60
        "Arms Window Title": EbMiscTextString(default_offset=0x0439C6, maximum_size=4),                              #C45c68
        "Other Window Title": EbMiscTextString(default_offset=0x0439CA, maximum_size=4),                             #C45c70
        "No Equip": EbMiscTextString(default_offset=0x0439CE, maximum_size=4),                                       #C45c78
        "Unequip": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x1A7FA)], maximum_size=7, null_terminated=True), #C1A912
        # v This one could possibly have a larger max size, I haven't tested
        "To": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x1A9F0)], maximum_size=3, null_terminated=False)       #C1AB1A
    },
    "Item Menu": {
        "Use": EbMiscTextString(default_offset=0x0432D6, maximum_size=5),    #C43550
        "Give": EbMiscTextString(default_offset=0x0432DB, maximum_size=5),   #C43556
        "Drop": EbMiscTextString(default_offset=0x0432E0, maximum_size=5),   #C4355c
        "Help": EbMiscTextString(default_offset=0x0432E5, maximum_size=5)    #C43562
    },
    "Menu Action Targets": {
        "Who": EbMiscTextString(default_offset=0x043761, maximum_size=4),    #C45963
        "Which": EbMiscTextString(default_offset=0x043765, maximum_size=4),  #C4596d
        "Where": EbMiscTextString(default_offset=0x043769, maximum_size=4),  #C45977
        "Whom": EbMiscTextString(default_offset=0x04376D, maximum_size=4),   #C45981
        "Where 2": EbMiscTextString(default_offset=0x043771, maximum_size=4) #C4598b
    },
    "Window Titles": {
        "Escargo Express Window Title": EbMiscTextString(default_offset=0x0439AB, maximum_size=6),       #C45c10
        "Phone Window Title": EbMiscTextString(pointers=[EbMiscTextAsmPointer(0x19508)], maximum_size=4) #C1945B
    }
}


class MiscTextModule(EbModule):
    NAME = "Miscellaneous Text"

    def __init__(self):
        super(MiscTextModule, self).__init__()
        self.data = dict()

    def read_from_rom(self, rom):
        for category_name, category in MISC_TEXT.items():
            category_data = dict()
            for item_name, item in category.items():
                category_data[item_name] = item.from_block(rom)
            self.data[category_name] = category_data

    def write_to_rom(self, rom):
        for category_name, category in sorted(MISC_TEXT.items()):
            for item_name, item in sorted(category.items()):
                item.to_block(rom, self.data[category_name][item_name])

    def read_from_project(self, resource_open):
        with resource_open("text_misc", "yml", True) as f:
            self.data = yml_load(f)

    def write_to_project(self, resource_open):
        with resource_open("text_misc", "yml", True) as f:
            yml_dump(self.data, f, default_flow_style=False)

    def upgrade_project(self, old_version, new_version, rom, resource_open_r, resource_open_w, resource_delete):
        if old_version == new_version:
            return
        elif old_version == 4:
            self.read_from_project(resource_open_r)

            item = MISC_TEXT["Battle Menu"]["Do Nothing"]
            self.data["Battle Menu"]["Do Nothing"] = item.from_block(rom)

            self.write_to_project(resource_open_w)

            self.upgrade_project(old_version + 1, new_version, rom, resource_open_r, resource_open_w, resource_delete)
        elif old_version <= 2:
            self.read_from_rom(rom)
            self.write_to_project(resource_open_w)
            self.upgrade_project(3, new_version, rom, resource_open_r, resource_open_w, resource_delete)
        else:
            self.upgrade_project(old_version + 1, new_version, rom, resource_open_r, resource_open_w, resource_delete)
