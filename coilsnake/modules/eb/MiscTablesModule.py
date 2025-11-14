import logging

from coilsnake.model.eb.table import eb_table_from_offset
from coilsnake.modules.eb.EbModule import EbModule
from coilsnake.util.common.yml import convert_values_to_hex_repr, replace_field_in_yml, yml_load, yml_dump
from coilsnake.util.eb.pointer import from_snes_address

log = logging.getLogger(__name__)


class MiscTablesModule(EbModule):
    NAME = "Miscellaneous Tables"
    TABLE_OFFSETS = [
        0xC3F8C3,  # Attract mode text                          $C3FD8D
        0xD5F5A5,  # Timed Item Delivery                        $D5F645
        0xE123E1,  # Photographer                               $E12F8A
        0xD5E9D7,  # Condiment Table                            $D5EA77
        0xD5EB0B,  # Scripted Teleport Destination Table        $D5EBAB
        0xD5F25B,  # Hotspots Table                             $D5F2FB
        0xC3F02E,  # Playable Character Graphics Control Table  $C3F2B5
        0xD59A06,  # PSI Abilities                              $D58A50
        0xD58B1E,  # Battle Actions Table                       $D57B68
        0xD5E9BB,  # Statistic Growth Variables                 $D5EA5B
        0xD59E00,  # Level-up EXP Table                         $D58F49
        0xD5F555,  # Initial Stats Table                        $D5F5F5
        0xD5899E,  # PSI Teleport Destination Table             $D57880
        0xD58AC8,  # Phone Contacts Table                       $D57AAE
        0xD587D0,  # Store Inventory Table                      $D576B2
        0xD5F41B,  # Timed Item Transformations                 $D5F4BB
        0xD5F42F,  # Don't Care                                 $D5F4CF
        0xD57000,  # Item Data                                  $D55000
        0xC2302E,  # Consolation Item                           $C23109
        0xC3E23A,  # Windows                                    $C3E250
    ]

    def __init__(self):
        super(MiscTablesModule, self).__init__()
        self.tables = [(from_snes_address(x), eb_table_from_offset(x)) for x in self.TABLE_OFFSETS]

    def read_from_rom(self, rom):
        for offset, table in self.tables:
            table.from_block(rom, offset)

    def write_to_rom(self, rom):
        for offset, table in self.tables:
            table.to_block(rom, offset)

    def read_from_project(self, resource_open):
        for _, table in self.tables:
            with resource_open(table.name.lower(), "yml", True) as f:
                log.debug("Reading {}.yml".format(table.name.lower()))
                table.from_yml_file(f)

    def write_to_project(self, resource_open):
        for _, table in self.tables:
            with resource_open(table.name.lower(), "yml", True) as f:
                table.to_yml_file(f)

    def upgrade_project(self, old_version, new_version, rom, resource_open_r, resource_open_w, resource_delete):
        if old_version == new_version:
            return
        elif old_version == 3:
            replace_field_in_yml(resource_name="item_configuration_table",
                                 resource_open_r=resource_open_r,
                                 resource_open_w=resource_open_w,
                                 key="Effect",
                                 new_key="Action")
            replace_field_in_yml(resource_name="psi_ability_table",
                                 resource_open_r=resource_open_r,
                                 resource_open_w=resource_open_w,
                                 key="Effect",
                                 new_key="Action")
            replace_field_in_yml(resource_name="psi_ability_table",
                                 resource_open_r=resource_open_r,
                                 resource_open_w=resource_open_w,
                                 key="PSI Name",
                                 value_map={0: None,
                                            1: 0,
                                            2: 1,
                                            3: 2,
                                            4: 3,
                                            5: 4,
                                            6: 5,
                                            7: 6,
                                            8: 7,
                                            9: 8,
                                            10: 9,
                                            11: 10,
                                            12: 11,
                                            13: 12,
                                            14: 13,
                                            15: 14,
                                            16: 15,
                                            17: 16})

            resource_delete("cmd_window_text")
            resource_delete("psi_anim_palettes")
            resource_delete("sound_stone_palette")

            self.upgrade_project(old_version=old_version + 1,
                                 new_version=new_version,
                                 rom=rom,
                                 resource_open_r=resource_open_r,
                                 resource_open_w=resource_open_w,
                                 resource_delete=resource_delete)
        elif old_version == 2:
            replace_field_in_yml(resource_name="timed_delivery_table",
                                 resource_open_r=resource_open_r,
                                 resource_open_w=resource_open_w,
                                 key="Suitable Area Text Pointer",
                                 new_key="Delivery Success Text Pointer")
            replace_field_in_yml(resource_name="timed_delivery_table",
                                 resource_open_r=resource_open_r,
                                 resource_open_w=resource_open_w,
                                 key="Unsuitable Area Text Pointer",
                                 new_key="Delivery Failure Text Pointer")

            with resource_open_r("timed_delivery_table", "yml", True) as f:
                out = yml_load(f)
                yml_str_rep = yml_dump(out, default_flow_style=False)

            yml_str_rep = convert_values_to_hex_repr(yml_str_rep, "Event Flag")

            with resource_open_w("timed_delivery_table", "yml", True) as f:
                f.write(yml_str_rep)

            self.upgrade_project(old_version=old_version + 1,
                                 new_version=new_version,
                                 rom=rom,
                                 resource_open_r=resource_open_r,
                                 resource_open_w=resource_open_w,
                                 resource_delete=resource_delete)
        elif old_version == 1:
            replace_field_in_yml(resource_name="psi_ability_table",
                                 resource_open_r=resource_open_r,
                                 resource_open_w=resource_open_w,
                                 key="Target",
                                 new_key="Usability Outside of Battle",
                                 value_map={"Nobody": "Other",
                                            "Enemies": "Unusable",
                                            "Allies": "Usable"})
            replace_field_in_yml(resource_name="battle_action_table",
                                 resource_open_r=resource_open_r,
                                 resource_open_w=resource_open_w,
                                 key="Direction",
                                 value_map={"Party": "Enemy",
                                            "Enemy": "Party"})

            self.upgrade_project(old_version=old_version + 1,
                                 new_version=new_version,
                                 rom=rom,
                                 resource_open_r=resource_open_r,
                                 resource_open_w=resource_open_w,
                                 resource_delete=resource_delete)
        else:
            self.upgrade_project(old_version + 1, new_version, rom, resource_open_r, resource_open_w, resource_delete)
