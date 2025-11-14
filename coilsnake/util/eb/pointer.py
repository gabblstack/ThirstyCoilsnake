import logging
import re
from coilsnake.exceptions.common.exceptions import InvalidArgumentError

log = logging.getLogger(__name__)


def from_snes_address(address):
    if address < 0:
        raise InvalidArgumentError("Invalid snes address[{:#x}]".format(address))
    elif address >= 0xc00000:
        return address - 0xc00000
    else:
        return address


def to_snes_address(address):
    if address >= 0x400000:
        return address
    else:
        return address + 0xc00000


def read_asm_pointer(block, offset):
    part1 = block[offset + 1] | (block[offset + 2] << 8)
    part2 = block[offset + 6] | (block[offset + 7] << 8)
    return part1 | (part2 << 16)

def read_xl_pointer(block, offset):
    return block[offset + 1] | (block[offset + 2] << 8) | (block[offset + 3] << 16)

def write_asm_pointer(block, offset, pointer):
    block[offset + 1] = pointer & 0xff
    block[offset + 2] = (pointer >> 8) & 0xff
    block[offset + 6] = (pointer >> 16) & 0xff
    block[offset + 7] = (pointer >> 24) & 0xff

def write_xl_pointer(block, offset, pointer):
    block[offset + 1] = pointer & 0xff
    block[offset + 2] = (pointer >> 8) & 0xff
    block[offset + 3] = (pointer >> 16) & 0xff

class PointerReference:
    POINTER_STR = "pointer"
    READ_IMPL = None
    WRITE_IMPL = None

    def __init__(self, offset):
        self.offset = offset

    def validate_structure(self, rom):
        raise NotImplementedError("Please use a child class of PointerReference")

    def read(self, rom):
        address = self.READ_IMPL(rom, self.offset)
        log.info("Read %s at %#x, value is %#06x", self.POINTER_STR, self.offset, address)
        return address

    def write(self, rom, address):
        log.info("Writing %s at %#x, value is %#06x", self.POINTER_STR, self.offset, address)
        self.WRITE_IMPL(rom, self.offset, address)


class AsmPointerReference(PointerReference):
    POINTER_STR = "ASM pointer"
    READ_IMPL = staticmethod(read_asm_pointer)
    WRITE_IMPL = staticmethod(write_asm_pointer)

    POINTER_FORMAT = re.compile(
        rb'''[\xa9\xa2\xa0]..  # Match LDA_i / LDX_i / LDY_i
             [\x85\x86\x84](.) # Match STA_d / STX_d / STY_d
             [\xa9\xa2\xa0]..  # Match LDA_i / LDX_i / LDY_i
             [\x85\x86\x84](.) # Match STA_d / STX_d / STY_d
        ''', re.VERBOSE | re.DOTALL)

    def validate_structure(self, rom):
        region = bytes(rom.to_array()[self.offset:self.offset+10])
        m = self.POINTER_FORMAT.match(region)
        if m:
            # The code has the correct overall structure.
            # However, it's possible that it could be coincidence.
            # Check if we're storing to sequential spots in the DP.
            # If we are, assume that the code hasn't been patched.
            dpLo, dpHi = m.groups()
            # Unfortunately, these are `bytes` objects with length 1, hence the [0]
            return dpLo[0] + 2 == dpHi[0]
        # The structure of the reference is incorrect.
        # The code must have been changed somewhere else - don't patch.
        return False

class XlPointerReference(PointerReference):
    POINTER_STR = "XL pointer"
    READ_IMPL = staticmethod(read_xl_pointer)
    WRITE_IMPL = staticmethod(write_xl_pointer)

    def __init__(self, offset, expected_opcode=None):
        super().__init__(offset)
        self.expected_opcode = expected_opcode

    def validate_structure(self, rom):
        opcode = rom[self.offset]
        if self.expected_opcode:
            return opcode == self.expected_opcode
        else:
            # The 65816 opcodes are pretty regular - check out this neat trick
            return opcode & 0x0F == 0x0F
