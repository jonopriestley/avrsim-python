from avr_pos import *
from avr_lexer import *
from avr_error import RETError

######################################
#  INTERPRETER
######################################

class Interpreter:
    def __init__(self, dmem, pmem, fn, inst_length):
        self.dmem = dmem
        self.pmem = pmem
        self.fn = fn
        self.pos = Position(-1, 0, -1, fn, self.pmem)
        self.inst_length = inst_length # number of instructions before all NOPs
        self.file_end = False # have you executed the whole file

        self.pcl = self.dmem[0x5B] # PC low
        self.pch = self.dmem[0x5C] # PC high

        self.sreg = self.dmem[0x5F]
        self.sph = self.dmem[0x5E]
        self.spl = self.dmem[0x5D]

        self.current_inst = self.pmem[self.get_pc_val()]

        self.pmem_length = len(self.pmem)
        self.dmem_length = len(self.dmem)

        self.pushpop = [0] # counting (pushes - pops) for each subroutine layer

    def copy(self):
        return Interpreter(self.dmem, self.pmem, self.fn, self.inst_length)

    def step(self):
        if (not self.file_end) and (self.get_pc_val() < self.pmem_length):
            # Executes instruction and updates PC and SREG
            self.current_inst = self.pmem[self.get_pc_val()] # set current instruction
            inst = self.current_inst[0] # set instruction name

        else: self.file_end = True

        if self.file_end:
            pass

        elif inst == 'ADC':
            Rd = self.dmem[int(self.current_inst[1][1:])].value # get Rr value
            Rr = self.dmem[int(self.current_inst[2][1:])].value # get Rd value
            C = int(self.sreg.value[7]) # get carry bit
            R = (Rd + Rr + C) % 256 # calculate result
            Rd = self.make_8_bit_binary(Rd)
            
            self.dmem[int(self.current_inst[1][1:])].set_value(R) # set result register value
            self.update_pc_val(self.get_pc_val() + 1) # increment PC
            
            Rr = self.make_8_bit_binary(Rr)
            R = self.make_8_bit_binary(R)
            self.sreg.value[2] = int((int(Rd[4]) & int(Rr[4])) | (int(Rr[4]) & (1 - int(R[4]))) | (int(Rd[4]) & (1 - int(R[4]))))
            self.sreg.value[4] = int((int(Rd[0]) & int(Rr[0]) & (1 - int(R[0]))) | ((1 - int(Rd[0])) & (1 - int(Rr[0])) & int(R[0])))
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')
            self.sreg.value[7] = int((int(Rd[0]) & int(Rr[0])) | (int(Rr[0]) & (1 - int(R[0]))) | (int(Rd[0]) & (1 - int(R[0]))))

        elif inst == 'ADD':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            R = (Rd + Rr) % 256
            Rd = self.make_8_bit_binary(Rd)

            self.dmem[int(self.current_inst[1][1:])].set_value(R)
            self.update_pc_val(self.get_pc_val() + 1)

            Rr = self.make_8_bit_binary(Rr)
            R = self.make_8_bit_binary(R)
            self.sreg.value[2] = int((int(Rd[4]) & int(Rr[4])) | (int(Rr[4]) & (1 - int(R[4]))) | (int(Rd[4]) & (1 - int(R[4]))))
            self.sreg.value[4] = int((int(Rd[0]) & int(Rr[0]) & (1 - int(R[0]))) | ((1 - int(Rd[0])) & (1 - int(Rr[0])) & int(R[0])))
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')
            self.sreg.value[7] = int((int(Rd[0]) & int(Rr[0])) | (int(Rr[0]) & (1 - int(R[0]))) | (int(Rd[0]) & (1 - int(R[0]))))

        elif inst == 'AND':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            R = Rd & Rr

            self.dmem[int(self.current_inst[1][1:])].set_value(R)
            self.update_pc_val(self.get_pc_val() + 1)

            R = self.make_8_bit_binary(R)
            self.sreg.value[4] = 0
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')
        
        elif inst == 'ANDI':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            K = int(self.current_inst[2])
            R = Rd & K

            self.dmem[int(self.current_inst[1][1:])].set_value(R)
            self.update_pc_val(self.get_pc_val() + 1)

            R = self.make_8_bit_binary(R)
            self.sreg.value[4] = 0
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')

        elif inst == 'BCLR':
            s = int(self.current_inst[1])
            self.sreg.value[7 - s] = 0
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRBC':
            s = int(self.current_inst[1])
            k = int(self.current_inst[2])
            if (self.sreg.value[7 - s] == 0): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRBS':
            s = int(self.current_inst[1])
            k = int(self.current_inst[2])
            if (self.sreg.value[7 - s] == 1): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRCC':
            k = int(self.current_inst[1])
            if (self.sreg.value[7] == 0): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRCS':
            k = int(self.current_inst[1])
            if (self.sreg.value[7] == 1): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BREQ':
            k = int(self.current_inst[1])
            if (self.sreg.value[6] == 1): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRGE':
            k = int(self.current_inst[1])
            if (self.sreg.value[4] ^ self.sreg.value[5] == 0): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRHC':
            k = int(self.current_inst[1])
            if (self.sreg.value[2] == 0): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRHS':
            k = int(self.current_inst[1])
            if (self.sreg.value[2] == 1): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRID':
            k = int(self.current_inst[1])
            if (self.sreg.value[0] == 0): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRIE':
            k = int(self.current_inst[1])
            if (self.sreg.value[0] == 1): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRLO':
            k = int(self.current_inst[1])
            if (self.sreg.value[7] == 1): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRLT':
            k = int(self.current_inst[1])
            if (self.sreg.value[4] ^ self.sreg.value[5] == 1): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRMI':
            k = int(self.current_inst[1])
            if (self.sreg.value[5] == 1): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRNE':
            k = int(self.current_inst[1])
            if (self.sreg.value[6] == 0): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRPL':
            k = int(self.current_inst[1])
            if (self.sreg.value[5] == 0): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)
            
        elif inst == 'BRSH':
            k = int(self.current_inst[1])
            if (self.sreg.value[7] == 0): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRTC':
            k = int(self.current_inst[1])
            if (self.sreg.value[1] == 0): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRTS':
            k = int(self.current_inst[1])
            if (self.sreg.value[1] == 1): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRVC':
            k = int(self.current_inst[1])
            if (self.sreg.value[4] == 0): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BRVS':
            k = int(self.current_inst[1])
            if (self.sreg.value[4] == 1): self.update_pc_val(self.get_pc_val() + k + 1)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'BSET':
            s = int(self.current_inst[1])
            self.sreg.value[7 - s] = 1
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'CALL':
            self.update_pc_val(self.get_pc_val() + 2) # same for both if/else statements

            if self.current_inst[1] not in FUNCTIONS:
                self.decrement_SP()
                self.dmem[self.get_SP()] = self.pcl.value # adding to stack
                self.decrement_SP()
                self.dmem[self.get_SP()] = self.pch.value # adding to stack
                self.decrement_SP()
                self.dmem[self.get_SP()] = 0 # adding to stack the 3rd byte
                k = int(self.current_inst[1])
                self.update_pc_val(k)
                self.pushpop[-1] += 3
                self.pushpop.append(0)

            elif self.current_inst[1] == 'PRINTF':
                ### Pop
                STACK = self.dmem[self.get_SP()] 
                self.dmem[26].set_value(STACK) # R26 = Xlow = STACK
                self.increment_SP()
                Xlow = STACK

                STACK = self.dmem[self.get_SP()]
                self.dmem[27].set_value(STACK) # R27 = Xhigh = STACK
                self.increment_SP()
                Xhigh = STACK

                ### Print
                printed_string = ''
                while True:
                    XYZ = 'X+'
                    val = self.get_XYZ(XYZ) + 0x100 # dmem value in XYZ
                    self.increment_XYZ(XYZ) # increments XYZ if necessary
                    K = self.dmem[val]
                    if K == 0:
                        break
                    char = chr(K)
                    print(char, end = '') # prints the value
                    printed_string += char
                # print('') -> could be used to add \n to end of each line

                ### Push
                Rr = self.dmem[27].value
                self.decrement_SP()
                self.dmem[self.get_SP()] = Rr
                #self.dmem[27].set_value(Xhigh) # reset the value of R27 to what it was so it isnt disturbed

                Rr = self.dmem[26].value
                self.decrement_SP()
                self.dmem[self.get_SP()] = Rr
                #self.dmem[26].set_value(Xlow) # reset the value of R26 to what it was so it isnt disturbed

                return printed_string

        elif inst == 'CBI':
            A = int(self.current_inst[1]) + 0x20
            b = int(self.current_inst[2])
            self.dmem[A].clear_bit(b)
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'CBR':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            K = int(self.current_inst[2])
            R = Rd & (0xFF - K)

            self.dmem[int(self.current_inst[1][1:])].set_value(R)
            self.update_pc_val(self.get_pc_val() + 1)

            R = self.make_8_bit_binary(R)
            self.sreg.value[4] = 0
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')

        elif inst == 'CLC':
            self.sreg.value[7] = 0
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'CLH':
            self.sreg.value[2] = 0
            self.update_pc_val(self.get_pc_val() + 1)
            
        elif inst == 'CLI':
            self.sreg.value[0] = 0
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'CLN':
            self.sreg.value[5] = 0
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'CLR':
            self.dmem[int(self.current_inst[1][1:])].set_value(0)
            self.update_pc_val(self.get_pc_val() + 1)
            self.sreg.value[3] = 0
            self.sreg.value[4] = 0
            self.sreg.value[5] = 0
            self.sreg.value[6] = 1

        elif inst == 'CLS':
            self.sreg.value[3] = 0
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'CLT':
            self.sreg.value[1] = 0
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'CLV':
            self.sreg.value[4] = 0
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'CLZ':
            self.sreg.value[6] = 0
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'COM':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            R = 0xFF - Rd

            self.dmem[int(self.current_inst[1][1:])].set_value(R)
            self.update_pc_val(self.get_pc_val() + 1)

            self.sreg.value[4] = 0
            self.sreg.value[5] = int(R > 127)
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == 0)
            self.sreg.value[7] = 1

        elif inst == 'CP':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            R = (Rd - Rr) % 256

            self.update_pc_val(self.get_pc_val() + 1)

            Rd = self.make_8_bit_binary(Rd)
            Rr = self.make_8_bit_binary(Rr)
            R = self.make_8_bit_binary(R)
            self.sreg.value[2] = int((int(Rr[4]) & int(R[4])) | (int(Rr[4]) & (1 - int(Rd[4]))) | (int(R[4]) & (1 - int(Rd[4]))))
            self.sreg.value[4] = int((int(Rr[0]) & int(R[0]) & (1 - int(Rd[0]))) | ((1 - int(Rr[0])) & (1 - int(R[0])) & int(Rd[0])))
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')
            self.sreg.value[7] = int((int(Rr[0]) & int(R[0])) | (int(Rr[0]) & (1 - int(Rd[0]))) | (int(R[0]) & (1 - int(Rd[0]))))
        
        elif inst == 'CPC':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            C = self.sreg.value[7]
            R = (Rd - Rr - C) % 256

            self.update_pc_val(self.get_pc_val() + 1)

            Rd = self.make_8_bit_binary(Rd)
            Rr = self.make_8_bit_binary(Rr)
            R = self.make_8_bit_binary(R)
            self.sreg.value[2] = int((int(Rr[4]) & int(R[4])) | (int(Rr[4]) & (1 - int(Rd[4]))) | (int(R[4]) & (1 - int(Rd[4]))))
            self.sreg.value[4] = int((int(Rr[0]) & int(R[0]) & (1 - int(Rd[0]))) | ((1 - int(Rr[0])) & (1 - int(R[0])) & int(Rd[0])))
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int((R == '00000000') & (self.sreg.value[6]))
            self.sreg.value[7] = int((int(Rr[0]) & int(R[0])) | (int(Rr[0]) & (1 - int(Rd[0]))) | (int(R[0]) & (1 - int(Rd[0]))))
            
        elif inst == 'CPI':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            K = int(self.current_inst[2])
            R = (Rd - K) % 256

            self.update_pc_val(self.get_pc_val() + 1)

            Rd = self.make_8_bit_binary(Rd)
            K = self.make_8_bit_binary(K)
            R = self.make_8_bit_binary(R)
            self.sreg.value[2] = int((int(K[4]) & int(R[4])) | (int(K[4]) & (1 - int(Rd[4]))) | (int(R[4]) & (1 - int(Rd[4]))))
            self.sreg.value[4] = int((int(K[0]) & int(R[0]) & (1 - int(Rd[0]))) | ((1 - int(K[0])) & (1 - int(R[0])) & int(Rd[0])))
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')
            self.sreg.value[7] = int((int(K[0]) & int(R[0])) | (int(K[0]) & (1 - int(Rd[0]))) | (int(R[0]) & (1 - int(Rd[0]))))

        elif inst == 'DEC':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            R = (Rd - 1) % 256
            self.dmem[int(self.current_inst[1][1:])].set_value(R)

            self.update_pc_val(self.get_pc_val() + 1)

            R = self.make_8_bit_binary(R)
            self.sreg.value[4] = int(R == '01111111')
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')

        elif inst == 'EOR':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            R = Rd ^ Rr

            self.dmem[int(self.current_inst[1][1:])].set_value(R)
            self.update_pc_val(self.get_pc_val() + 1)

            R = self.make_8_bit_binary(R)
            self.sreg.value[4] = 0
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')

        elif inst == 'IN':
            A = self.dmem[int(self.current_inst[2]) + 0x20].value
            self.dmem[int(self.current_inst[1][1:])].set_value(A)
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'INC':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            R = (Rd + 1) % 256
            self.dmem[int(self.current_inst[1][1:])].set_value(R)

            self.update_pc_val(self.get_pc_val() + 1)

            R = self.make_8_bit_binary(R)
            self.sreg.value[4] = int(R == '10000000')
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')

        elif inst == 'JMP':
            k = int(self.current_inst[1])
            self.update_pc_val(k)

        elif inst == 'LD':
            XYZ = self.current_inst[2]
            self.decrement_XYZ(XYZ) # decrements XYZ if necessary
            val = self.get_XYZ(XYZ) + 0x100 # dmem value in XYZ
            K = self.dmem[val]
            self.dmem[int(self.current_inst[1][1:])].set_value(K)
            self.update_pc_val(self.get_pc_val() + 1)
            self.increment_XYZ(XYZ) # increments XYZ if necessary
        
        elif inst == 'LDD':
            XYZ = self.current_inst[2]
            q = int(self.current_inst[3])
            val = self.get_XYZ(XYZ) + 0x100 + q # dmem value in XYZ
            K = self.dmem[val]
            self.dmem[int(self.current_inst[1][1:])].set_value(K)
            self.update_pc_val(self.get_pc_val() + 1)
        
        elif inst == 'LDI':
            K = int(self.current_inst[2])
            self.dmem[int(self.current_inst[1][1:])].set_value(K)
            self.update_pc_val(self.get_pc_val() + 1)
        
        elif inst == 'LDS':
            k = self.dmem[int(self.current_inst[2]) + 0x100]
            self.dmem[int(self.current_inst[1][1:])].set_value(k)
            self.update_pc_val(self.get_pc_val() + 2)
        
        elif inst == 'LSL':
            R = self.make_8_bit_binary(self.dmem[int(self.current_inst[1][1:])].value)
            Rd = R + '0'
            C = int(Rd[0])
            Rd = int(Rd[1:], 2)
            self.dmem[int(self.current_inst[1][1:])].set_value(Rd)

            self.update_pc_val(self.get_pc_val() + 1)

            self.sreg.value[2] = int(R[4])
            self.sreg.value[5] = int(R[0])
            self.sreg.value[7] = C
            self.sreg.value[4] = self.sreg.value[5] ^ self.sreg.value[7]
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')

        elif inst == 'LSR':
            R = '0' + self.make_8_bit_binary(self.dmem[int(self.current_inst[1][1:])].value)
            C = int(R[8])
            Rd = int(R[:8], 2)
            self.dmem[int(self.current_inst[1][1:])].set_value(Rd)

            self.update_pc_val(self.get_pc_val() + 1)

            self.sreg.value[5] = 0
            self.sreg.value[7] = C
            self.sreg.value[4] = self.sreg.value[5] ^ self.sreg.value[7]
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R[:8] == '00000000')

        elif inst == 'MOV':
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            self.dmem[int(self.current_inst[1][1:])].set_value(Rr)
            self.update_pc_val(self.get_pc_val() + 1)
        
        elif inst == 'MUL':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            R = Rd * Rr
            R0 = R % 256
            R1 = int((R - R0) / 256)

            self.dmem[0].set_value(R0)
            self.dmem[1].set_value(R1)
            self.update_pc_val(self.get_pc_val() + 1)

            self.sreg.value[6] = int(R == 0)
            self.sreg.value[7] = int(R >= 32768)

        elif inst == 'MULS':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            R = Rd * Rr
            R0 = R % 256
            R1 = int((R - R0) / 256)

            self.dmem[0].set_value(R0)
            self.dmem[1].set_value(R1)
            self.update_pc_val(self.get_pc_val() + 1)

            self.sreg.value[6] = int(R == 0)
            self.sreg.value[7] = int(R >= 32768)

        elif inst == 'MULSU':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            R = Rd * Rr
            R0 = R % 256
            R1 = int((R - R0) / 256)

            self.dmem[0].set_value(R0)
            self.dmem[1].set_value(R1)
            self.update_pc_val(self.get_pc_val() + 1)

            self.sreg.value[6] = int(R == 0)
            self.sreg.value[7] = int(R >= 32768)

        elif inst == 'NEG':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            R = (0x00 - Rd) % 256
            Rd = self.make_8_bit_binary(Rd)

            self.dmem[int(self.current_inst[1][1:])].set_value(R)
            self.update_pc_val(self.get_pc_val() + 1)

            R = self.make_8_bit_binary(R)
            self.sreg.value[2] = int(int(R[4]) | (1 - int(Rd[4])))
            self.sreg.value[4] = int(R == '10000000')
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R != '00000000')

        elif inst == 'NOP':
            self.update_pc_val(self.get_pc_val() + 1)
        
        elif inst == 'OR':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            R = Rd | Rr

            self.dmem[int(self.current_inst[1][1:])].set_value(R)
            self.update_pc_val(self.get_pc_val() + 1)

            R = self.make_8_bit_binary(R)
            self.sreg.value[4] = 0
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')

        elif inst == 'ORI':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            K = int(self.current_inst[2])
            R = Rd | K

            self.dmem[int(self.current_inst[1][1:])].set_value(R)
            self.update_pc_val(self.get_pc_val() + 1)

            R = self.make_8_bit_binary(R)
            self.sreg.value[4] = 0
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')

        elif inst == 'OUT':
            Rd = self.dmem[int(self.current_inst[2][1:])].value
            A = int(self.current_inst[1]) + 0x20
            self.dmem[A].set_value(Rd)
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'POP':
            if self.pushpop[0] > 0: # check if the top layer has no elements left (ie nothing left in stack)
                STACK = self.dmem[self.get_SP()]
                self.dmem[int(self.current_inst[1][1:])].set_value(STACK)
                self.increment_SP()
                self.update_pc_val(self.get_pc_val() + 1)
                self.pushpop[-1] -= 1
            else:
                return RETError(self.get_pc_val(), 'No elements left to pop.')
            
        elif inst == 'PUSH':
            Rr = self.dmem[int(self.current_inst[1][1:])].value
            self.decrement_SP()
            self.dmem[self.get_SP()] = Rr
            self.update_pc_val(self.get_pc_val() + 1)
            self.pushpop[-1] += 1

        elif inst == 'RJMP':
            k = int(self.current_inst[1])
            self.update_pc_val(self.get_pc_val() + k + 1)

        elif inst == 'RET':

            # If stack pointer at end or all NOPs afterwards then end
            if (self.get_SP() == 0):
                self.file_end = True

            else:
                kHH = self.dmem[self.get_SP()]  # return location(3rd byte) from the stack
                self.increment_SP()
                kH = self.dmem[self.get_SP()]   # return location(high) from the stack
                self.increment_SP()
                kL = self.dmem[self.get_SP()]   # return location(low) from the stack
                self.increment_SP()
                if self.pushpop[-1] < 0:        # must have balanced stack pushes & pops to return correctly
                    return RETError(self.get_pc_val(), f'{-1 * self.pushpop[-1]} too many pops from the stack to return correctly.')
                elif self.pushpop[-1] > 0:        # must have balanced stack pushes & pops to return correctly
                    return RETError(self.get_pc_val(), f'{self.pushpop[-1]} too many pushes to the stack to return correctly.')
                
                self.pushpop.pop(-1)
                if len(self.pushpop) == 0:
                    self.file_end = True
                    
                else:
                    self.pushpop[-1] -= 3
                    self.update_pc_val((256 * kH) + kL)

        elif inst == 'ROL':
            R = self.make_8_bit_binary(self.dmem[int(self.current_inst[1][1:])].value) + str(self.sreg.value[7])
            C = int(R[0], 2)
            Rd = int(R[1:], 2)
            self.dmem[int(self.current_inst[1][1:])].set_value(Rd)

            self.update_pc_val(self.get_pc_val() + 1)

            self.sreg.value[2] = int(R[4])
            self.sreg.value[5] = int(R[1])
            self.sreg.value[6] = int(R[1:9] == '00000000')
            self.sreg.value[7] = C
            self.sreg.value[4] = self.sreg.value[5] ^ self.sreg.value[7]
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]

        elif inst == 'ROR':
            R = str(self.sreg.value[7]) + self.make_8_bit_binary(self.dmem[int(self.current_inst[1][1:])].value)
            C = int(R[8], 2)
            Rd = int(R[0:8], 2)
            self.dmem[int(self.current_inst[1][1:])].set_value(Rd)

            self.update_pc_val(self.get_pc_val() + 1)

            self.sreg.value[5] = int(R[0])
            self.sreg.value[6] = int(R[0:8] == '00000000')
            self.sreg.value[7] = C
            self.sreg.value[4] = self.sreg.value[5] ^ self.sreg.value[7]
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]

        elif inst == 'SBC':
            Rd = self.dmem[int(self.current_inst[1][1:])].value # get Rr value
            Rr = self.dmem[int(self.current_inst[2][1:])].value # get Rd value
            C = int(self.sreg.value[7]) # get carry bit
            R = (Rd - Rr - C) % 256 # calculate result
            Rd = self.make_8_bit_binary(Rd)
            
            self.dmem[int(self.current_inst[1][1:])].set_value(R) # set result register value
            self.update_pc_val(self.get_pc_val() + 1) # increment PC
            
            Rr = self.make_8_bit_binary(Rr)
            R = self.make_8_bit_binary(R)
            self.sreg.value[2] = int((int(R[4]) & int(Rr[4])) | (int(Rr[4]) & (1 - int(Rd[4]))) | (int(R[4]) & (1 - int(Rd[4]))))
            self.sreg.value[4] = int((int(R[0]) & int(Rr[0]) & (1 - int(Rd[0]))) | ((1 - int(R[0])) & (1 - int(Rr[0])) & int(Rd[0])))
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')
            self.sreg.value[7] = int((int(R[0]) & int(Rr[0])) | (int(Rr[0]) & (1 - int(Rd[0]))) | (int(R[0]) & (1 - int(Rd[0]))))

        elif inst == 'SBI':
            A = int(self.current_inst[1]) + 0x20
            b = int(self.current_inst[2])
            self.dmem[A].set_bit(b)
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'SBR':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            K = int(self.current_inst[2])
            R = Rd | K

            self.dmem[int(self.current_inst[1][1:])].set_value(R)
            self.update_pc_val(self.get_pc_val() + 1)

            R = self.make_8_bit_binary(R)
            self.sreg.value[4] = 0
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')

        elif inst == 'SEC':
            self.sreg.value[7] = 1
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'SEH':
            self.sreg.value[2] = 1
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'SEI':
            self.sreg.value[0] = 1
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'SEN':
            self.sreg.value[5] = 1
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'SER':
            self.dmem[int(self.current_inst[1][1:])].set_value(0xFF)
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'SES':
            self.sreg.value[3] = 1
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'SET':
            self.sreg.value[1] = 1
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'SEV':
            self.sreg.value[4] = 1
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'SEZ':
            self.sreg.value[6] = 1
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'ST':
            XYZ = self.current_inst[1]
            self.decrement_XYZ(XYZ) # decrements XYZ if necessary
            val = self.get_XYZ(XYZ) + 0x100 # dmem value in XYZ
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            self.dmem[val] = Rr
            self.update_pc_val(self.get_pc_val() + 1)
            self.increment_XYZ(XYZ) # increments XYZ if necessary

        elif inst == 'STD':
            XYZ = self.current_inst[1]
            q = int(self.current_inst[2])
            val = self.get_XYZ(XYZ) + 0x100 + q # dmem value in XYZ
            Rr = self.dmem[int(self.current_inst[3][1:])].value
            self.dmem[val] = Rr
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'STS':
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            self.dmem[int(self.current_inst[1]) + 0x100] = Rr
            self.update_pc_val(self.get_pc_val() + 2)

        elif inst == 'SUB':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            R = (Rd - Rr) % 256
            Rd = self.make_8_bit_binary(Rd)

            self.dmem[int(self.current_inst[1][1:])].set_value(R)
            self.update_pc_val(self.get_pc_val() + 1)

            Rr = self.make_8_bit_binary(Rr)
            R = self.make_8_bit_binary(R)
            self.sreg.value[2] = int((int(R[4]) & int(Rr[4])) | (int(Rr[4]) & (1 - int(Rd[4]))) | (int(R[4]) & (1 - int(Rd[4]))))
            self.sreg.value[4] = int((int(R[0]) & int(Rr[0]) & (1 - int(Rd[0]))) | ((1 - int(R[0])) & (1 - int(Rr[0])) & int(Rd[0])))
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')
            self.sreg.value[7] = int((int(R[0]) & int(Rr[0])) | (int(Rr[0]) & (1 - int(Rd[0]))) | (int(R[0]) & (1 - int(Rd[0]))))

        elif inst == 'SUBI':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            K = int(self.current_inst[2])
            R = (Rd - K) % 256
            Rd = self.make_8_bit_binary(Rd)

            self.dmem[int(self.current_inst[1][1:])].set_value(R)
            self.update_pc_val(self.get_pc_val() + 1)

            K = self.make_8_bit_binary(K)
            R = self.make_8_bit_binary(R)
            self.sreg.value[2] = int((int(K[4]) & int(R[4])) | (int(K[4]) & (1 - int(Rd[4]))) | (int(R[4]) & (1 - int(Rd[4]))))
            self.sreg.value[4] = int((int(R[0]) & int(K[0]) & (1 - int(Rd[0]))) | ((1 - int(R[0])) & (1 - int(K[0])) & int(Rd[0])))
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')
            self.sreg.value[7] = int((int(K[0]) & int(R[0])) | (int(K[0]) & (1 - int(Rd[0]))) | (int(R[0]) & (1 - int(Rd[0]))))

        elif inst == 'SWAP':
            Rd = self.make_8_bit_binary(self.dmem[int(self.current_inst[1][1:])].value)
            Rd = Rd[4:8] + Rd[0:4]
            self.dmem[int(self.current_inst[1][1:])].set_value(int(Rd, 2))
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'XCH':
            Z = self.get_XYZ('Z') + 0x100
            Rd = self.dmem[int(self.current_inst[2][1:])].value
            
            self.dmem[int(self.current_inst[2][1:])].set_value(self.dmem[Z]) # Rd <- Z
            self.dmem[Z] = Rd # Z <- Rd

            self.update_pc_val(self.get_pc_val() + 1)

    def get_H(self, Rd3, Rr3, R3):
        Rd3 = int(Rd3)
        Rr3 = int(Rr3)
        R3 = int(R3)
        return int( (Rd3 & Rr3) | (Rr3 & (1 - R3)) | ((1 - R3) & Rd3) )

    def get_S(self, N, V):
        return int(N ^ V)

    def get_V(self, Rd7, Rr7, R7):
        Rd7 = int(Rd7)
        Rr7 = int(Rr7)
        R7 = int(R7)
        return int( (Rd7 & Rr7 & (1 - R7)) | ((1 - Rd7) & (1 - Rr7) & R7) )

    def get_N(self, R7):
        return int(R7)

    def get_Z(self, R):
        return int(int(R, 2) == 0)

    def get_C(self, Rd7, Rr7, R7):
        Rd7 = int(Rd7)
        Rr7 = int(Rr7)
        R7 = int(R7)
        return int( (Rd7 & Rr7) | (Rr7 & (1 - R7)) | ((1 - R7) & Rd7) )

    def get_XYZ(self, XYZ):
        if 'X' in XYZ:
            return (self.dmem[27].value * 256) + self.dmem[26].value
        elif 'Y' in XYZ:
            return (self.dmem[29].value * 256) + self.dmem[28].value
        elif 'Z' in XYZ:
            return (self.dmem[31].value * 256) + self.dmem[30].value

    def increment_XYZ(self, XYZ):
        regs = {'X': [26, 27], 'Y': [28, 29], 'Z': [30, 31]}

        if '+' in XYZ:
            L_idx = regs[XYZ[0]][0] # index of the low val
            H_idx = regs[XYZ[0]][1] # index of the high val
            L = self.dmem[L_idx].value # low val
            H = self.dmem[H_idx].value # high val
            if (L == 255):
                if (H == 255):
                    self.dmem[L_idx].set_value(0)
                    self.dmem[H_idx].set_value(0)
                else:
                    self.dmem[L_idx].set_value(0)
                    self.dmem[H_idx].set_value(H + 1)
            else:
                self.dmem[L_idx].set_value(L + 1)
           
    def decrement_XYZ(self, XYZ):
        regs = {'X': [26, 27], 'Y': [28, 29], 'Z': [30, 31]}
        
        if '-' in XYZ:
            L_idx = regs[XYZ[1]][0] # index of the low val
            H_idx = regs[XYZ[1]][1] # index of the high val
            L = self.dmem[L_idx].value # low val
            H = self.dmem[H_idx].value # high val
            if (L == 0):
                if (H == 0):
                    self.dmem[L_idx].set_value(255)
                    self.dmem[H_idx].set_value(255)
                else:
                    self.dmem[L_idx].set_value(255)
                    self.dmem[H_idx].set_value(H - 1)
            else:
                self.dmem[L_idx].set_value(L - 1) 

    def increment_SP(self):
        L = (self.dmem_length - 1) % 256
        H = int((self.dmem_length - (L)) / 256)
        if (self.spl.value == 255):
            if (self.sph.value == H):
                self.spl.set_value(0)
                self.sph.set_value(0)
            else:
                self.spl.set_value(0)
                self.sph.set_value(self.sph.value + 1)
        else:
            self.spl.set_value(self.spl.value + 1)

    def decrement_SP(self):
        L = (self.dmem_length - 1) % 256
        H = int((self.dmem_length - (L)) / 256)
        if (self.spl.value == 0):
            if (self.sph.value == 0):
                self.spl.set_value(255)
                self.sph.set_value(H)
            else:
                self.spl.set_value(255)
                self.sph.set_value(self.sph.value - 1)
        else:
            self.spl.set_value(self.spl.value - 1)

    def get_SP(self):
        return (256 * self.sph.value) + self.spl.value

    def make_8_bit_binary(self, integer):
        b = bin(integer)[2:]
        while len(b) < 8:
            b = '0' + b
        return b

    def update_pc_val(self, new_val):
        pos_start = self.pos.copy()
        if self.pcl.name != 'PCL': return UnexpectedValue(pos_start, self.pos, "Incorrect PC(low) location")
        if self.pch.name != 'PCH': return UnexpectedValue(pos_start, self.pos, "Incorrect PC(high) location")
        low_val = new_val % 256
        high_val = int((new_val - low_val) / 256)
        self.pcl.set_value(low_val)
        self.pch.set_value(high_val)

    def get_pc_val(self):
        pos_start = self.pos.copy()
        if self.pcl.name != 'PCL': return UnexpectedValue(pos_start, self.pos, "Incorrect PC(low) location")
        if self.pch.name != 'PCH': return UnexpectedValue(pos_start, self.pos, "Incorrect PC(high) location")
        return (256 * self.pch.value) + self.pcl.value

    def make_n_bit_binary(self, integer, n: int):
        """
        Returns binary value of length \'n\' without
        the \'0b\' at the front.
        """

        b = bin(int(integer))[2:]
        l = len(b)

        if l > n: return b[0:n+1]
        
        while l < n: # extending the length
            b = '0' + b
            l += 1
        return b

    def twos_comp(self, val, bits):
        """
        Returns the 2's comp of a value for
        a given number of bits.
        """

        if val >= 0:
            return '0' + self.make_n_bit_binary(val, bits - 1)
        
        b = bin((2 ** (bits - 1)) + val)[2:]    # flip bits and add 1
        
        l = len(b)
        while l < bits - 1:
            b = '0' + b
            l += 1
        b = '1' + b
        return b

    def get_binary_instruction(self, instruction: list):
        """
        Returns string or list of strings.
        """
        inst = instruction[0]

        if inst == 'ADC':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'000111{r[0]}{d}{r[1:]}'

        elif inst == 'ADD':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'000011{r[0]}{d}{r[1:]}'

        elif inst == 'AND':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'001000{r[0]}{d}{r[1:]}'
        
        elif inst == 'ANDI':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            K = self.make_n_bit_binary(instruction[2], 8) # reg number converted to binary
            return f'0111{K[0:4]}{d[1:]}{K[4:]}'

        elif inst == 'BCLR':
            s = self.make_n_bit_binary(instruction[1], 3)
            return f'100101001{s}1000'

        elif inst == 'BRBC':
            s = self.make_n_bit_binary(instruction[1], 3)
            k = self.twos_comp(instruction[2], 7)
            return f'111101{k}{s}'

        elif inst == 'BRBS':
            s = self.make_n_bit_binary(instruction[1], 3)
            k = self.twos_comp(instruction[2], 7)
            return f'111100{k}{s}'

        elif inst == 'BRCC':
            k = self.twos_comp(instruction[1], 7)
            return f'111101{k}000'

        elif inst == 'BRCS':
            k = self.twos_comp(instruction[1], 7)
            return f'111100{k}000'

        elif inst == 'BREQ':
            k = self.twos_comp(instruction[1], 7)
            return f'111100{k}001'

        elif inst == 'BRGE':
            k = self.twos_comp(instruction[1], 7)
            return f'111101{k}100'

        elif inst == 'BRHC':
            k = self.twos_comp(instruction[1], 7)
            return f'111101{k}101'

        elif inst == 'BRHS':
            k = self.twos_comp(instruction[1], 7)
            return f'111100{k}101'

        elif inst == 'BRID':
            k = self.twos_comp(instruction[1], 7)
            return f'111101{k}111'

        elif inst == 'BRIE':
            k = self.twos_comp(instruction[1], 7)
            return f'111100{k}111'

        elif inst == 'BRLO':
            k = self.twos_comp(instruction[1], 7)
            return f'111100{k}000'

        elif inst == 'BRLT':
            k = self.twos_comp(instruction[1], 7)
            return f'111100{k}100'

        elif inst == 'BRMI':
            k = self.twos_comp(instruction[1], 7)
            return f'111100{k}010'

        elif inst == 'BRNE':
            k = self.twos_comp(instruction[1], 7)
            return f'111101{k}001'

        elif inst == 'BRPL':
            k = self.twos_comp(instruction[1], 7)
            return f'111101{k}010'
            
        elif inst == 'BRSH':
            k = self.twos_comp(instruction[1], 7)
            return f'111101{k}000'

        elif inst == 'BRTC':
            k = self.twos_comp(instruction[1], 7)
            return f'111101{k}110'

        elif inst == 'BRTS':
            k = self.twos_comp(instruction[1], 7)
            return f'111100{k}110'

        elif inst == 'BRVC':
            k = self.twos_comp(instruction[1], 7)
            return f'111101{k}011'

        elif inst == 'BRVS':
            k = self.twos_comp(instruction[1], 7)
            return f'111100{k}011'

        elif inst == 'BSET':
            s = self.make_n_bit_binary(instruction[1], 3)
            return f'100101000{s}1000'

        elif inst == 'CALL':
            if instruction[1] == 'PRINTF':
                return ['1001010111111111', '1111111111111111']
            else:
                k = self.make_n_bit_binary(instruction[1], 22)
                return [f'1001010{k[0:5]}111{k[5]}', k[6:]]

        elif inst == 'CBI':
            A = self.make_n_bit_binary(instruction[1], 5)
            b = self.make_n_bit_binary(instruction[2], 3)
            return f'10011000{A}{b}'

        elif inst == 'CBR':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            K = self.make_n_bit_binary(255 - instruction[2], 8) # reg number converted to binary
            return f'0111{K[0:4]}{d[1:]}{K[4:]}'

        elif inst == 'CLC':
            return '1001010010001000'

        elif inst == 'CLH':
            return '1001010011011000'
            
        elif inst == 'CLI':
            return '1001010011111000'

        elif inst == 'CLN':
            return '1001010010101000'

        elif inst == 'CLR':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'001001{d[0]}{d}{d[1:]}'

        elif inst == 'CLS':
            return '1001010011001000'

        elif inst == 'CLT':
            return '1001010011101000'

        elif inst == 'CLV':
            return '1001010010111000'

        elif inst == 'CLZ':
            return '1001010010011000'

        elif inst == 'COM':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'1001010{d}0000'

        elif inst == 'CP':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'000101{r[0]}{d}{r[1:]}'

        elif inst == 'CPC':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'000001{r[0]}{d}{r[1:]}'

        elif inst == 'CPI':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            K = self.make_n_bit_binary(instruction[2], 8) # reg number converted to binary
            return f'0011{K[0:4]}{d[1:]}{K[4:]}'

        elif inst == 'DEC':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'1001010{d}1010'

        elif inst == 'EOR':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'001001{r[0]}{d}{r[1:]}'

        elif inst == 'IN':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            A = self.make_n_bit_binary(instruction[2], 6) # reg number converted to binary
            return f'10110{A[0:2]}{d}{A[2:]}'

        elif inst == 'INC':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'1001010{d}0011'

        elif inst == 'JMP':
            k = self.make_n_bit_binary(instruction[1], 22)
            return [f'1001010{k[0:5]}110{k[5]}', k[6:]]

        elif inst == 'LD':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            if instruction[2] == 'X':
                return f'1001000{d}1100'
            elif instruction[2] == 'X+':
                return f'1001000{d}1101'
            elif instruction[2] == '-X':
                return f'1001000{d}1110'
            elif instruction[2] == 'Y':
                return f'1000000{d}1000'
            elif instruction[2] == 'Y+':
                return f'1001000{d}1001'
            elif instruction[2] == '-Y':
                return f'1001000{d}1010'
            elif instruction[2] == 'Z':
                return f'1000000{d}0000'
            elif instruction[2] == 'Z+':
                return f'1001000{d}0001'
            elif instruction[2] == '-Z':
                return f'1001000{d}0010'
        
        elif inst == 'LDD':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            q = self.make_n_bit_binary(instruction[3], 6) # reg number converted to binary
            if instruction[2] == 'Y+':
                return f'10{q[0]}0{q[1:3]}0{d}1{q[3:]}'
            elif instruction[2] == 'Z+':
                return f'10{q[0]}0{q[1:3]}0{d}0{q[3:]}'
        
        elif inst == 'LDI':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            K = self.make_n_bit_binary(instruction[2], 8) # reg number converted to binary
            return f'1110{K[0:4]}{d[1:]}{K[4:]}'
        
        elif inst == 'LDS':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            k = self.make_n_bit_binary(instruction[2], 16) # reg number converted to binary
            return f'1001000{d}0000{k}'
        
        elif inst == 'LSL':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'000011{d[0]}{d}{d[1:]}'

        elif inst == 'LSR':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'1001010{d}0110'

        elif inst == 'MOV':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'001011{r[0]}{d}{r[1:]}'
        
        elif inst == 'MUL':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'100111{r[0]}{d}{r[1:]}'

        elif inst == 'MULS':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'00000010{d[1:]}{r[1:]}'

        elif inst == 'MULSU':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'000000110{d[2:]}0{r[2:]}'

        elif inst == 'NEG':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'1001010{d}0001'

        elif inst == 'NOP':
            return '0000000000000000'
        
        elif inst == 'OR':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'001010{r[0]}{d}{r[1:]}'

        elif inst == 'ORI':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            K = self.make_n_bit_binary(instruction[2], 8) # reg number converted to binary
            return f'0110{K[0:4]}{d[1:]}{K[4:]}'

        elif inst == 'OUT':
            A = self.make_n_bit_binary(instruction[1], 6) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'10111{A[0:2]}{r}{A[2:]}'

        elif inst == 'POP':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'1001000{d}1111'

        elif inst == 'PUSH':
            r = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'1001001{r}1111'

        elif inst == 'RET':
            return '1001010100001000'

        elif inst == 'ROL':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'000111{d[0]}{d}{d[1:]}'

        elif inst == 'ROR':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'1001010{d}0111'

        elif inst == 'SBC':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'000010{r[0]}{d}{r[1:]}'

        elif inst == 'SBI':
            A = self.make_n_bit_binary(instruction[1], 5)
            b = self.make_n_bit_binary(instruction[2], 3)
            return f'10011010{A}{b}'

        elif inst == 'SBR':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            K = self.make_n_bit_binary(instruction[2], 8) # reg number converted to binary
            return f'0110{K[0:4]}{d[1:]}{K[4:]}'

        elif inst == 'SEC':
            return '1001010000001000'

        elif inst == 'SEH':
            return '1001010001011000'

        elif inst == 'SEI':
            return '1001010001111000'

        elif inst == 'SEN':
            return '1001010000101000'

        elif inst == 'SER':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'11101111{d[1:]}1111'

        elif inst == 'SES':
            return '1001010001001000'

        elif inst == 'SET':
            return '1001010001101000'

        elif inst == 'SEV':
            return '1001010000111000'

        elif inst == 'SEZ':
            return '1001010000011000'

        elif inst == 'ST':
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            if instruction[1] == 'X':
                return f'1001001{r}1100'
            elif instruction[1] == 'X+':
                return f'1001001{r}1101'
            elif instruction[1] == '-X':
                return f'1001001{r}1110'
            elif instruction[1] == 'Y':
                return f'1000001{r}1000'
            elif instruction[1] == 'Y+':
                return f'1001001{r}1001'
            elif instruction[1] == '-Y':
                return f'1001001{r}1010'
            elif instruction[1] == 'Z':
                return f'1000001{r}0000'
            elif instruction[1] == 'Z+':
                return f'1001001{r}0001'
            elif instruction[1] == '-Z':
                return f'1001001{r}0010'

        elif inst == 'STD':
            r = self.make_n_bit_binary(instruction[3][1:], 5) # reg number converted to binary
            q = self.make_n_bit_binary(instruction[2], 6) # reg number converted to binary
            if instruction[1] == 'Y+':
                return f'10{q[0]}0{q[1:3]}1{r}1{q[3:]}'
            elif instruction[1] == 'Z+':
                return f'10{q[0]}0{q[1:3]}1{r}0{q[3:]}'

        elif inst == 'STS':
            k = self.make_n_bit_binary(instruction[1], 16) # reg number converted to binary
            d = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'1001001{d}0000{k}'

        elif inst == 'SUB':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'000110{r[0]}{d}{r[1:]}'

        elif inst == 'SUBI':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            K = self.make_n_bit_binary(instruction[2], 8) # reg number converted to binary
            return f'0101{K[0:4]}{d[1:]}{K[4:]}'

        elif inst == 'SWAP':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'1001010{d}0010'

        elif inst == 'XCH':
            d = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'1001001{d}0100'


