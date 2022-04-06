######################################
#  REGISTERS
######################################

class Register:
    def __init__(self, name, value=0):
        self.name = str(name) # eg 3 for R3
        self.value = value

    def __repr__(self):
        return f'{self.name}: {self.value}'

    def as_string(self):
        return f'{self.name}: {self.value}'

    def set_value(self, new_value):
        self.value = new_value % 256

    def get_bits(self): # returns as string
        """
        Returns as string
        """
        
        val = str(bin(self.value))[2:]
        while len(val) < 8:
            val = '0' + val
        return val

    def clr(self):
        self.set_value(0)

    def ser(self):
        self.set_value(255)

    def set_bit(self, bit):
        num = 2**bit
        self.value = self.value | num

    def clear_bit(self, bit):
        num = 255 - 2**bit
        self.value = self.value & num

    def com(self):
        self.set_value(255 - self.value)

    def neg(self):
        self.set_value(256 - self.value)

    def inc(self):
        self.set_value(self.value + 1)

    def dec(self):
        self.set_value(self.value - 1)


######################################
#  MEMORY
######################################

pmem_size = 0x4000 # max 0x3FFF
PMEM = [0x00 for i in range(pmem_size)]

dmem_size = 0x900 # max 0x8FF
DMEM = [0x00 for i in range(dmem_size)]


######################################
#  REGISTER FILE
######################################

for i in range(256):
    DMEM[i] = Register('R' + str(i))

SREG = Register('SREG')
SREG.value = [0, 0, 0, 0, 0, 0, 0, 0]

PCL = Register('PCL')
PCH = Register('PCH')


SPL = Register('SPL')
#SPL.set_value(L)
SPH = Register('SPH')
#SPH.set_value(H)

DMEM[0x5B] = PCL # program counter low byte
DMEM[0x5C] = PCH # program counter high byte
DMEM[0x5D] = SPL # stack pointer low byte (0x3D in I/O file)
DMEM[0x5E] = SPH # stack pointer high byte (0x3E in I/O file)
DMEM[0x5F] = SREG # status register (0x3F in I/O file)

REGISTER_FILE = []
for i in range(32):
    REGISTER_FILE.append(f'R{str(i)}')
