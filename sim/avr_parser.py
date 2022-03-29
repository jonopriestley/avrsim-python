from avr_lexer import *

######################################
#  PARSER
######################################

class Parser:
    def __init__(self, fn, lines, line_nums):
        self.fn = fn
        self.lines = lines
        self.line_nums = line_nums
        self.line_num = -1
        self.token_num = -1
        self.idx = -1
        self.pos = Position(-1, 0, -1, self.fn, self.lines)
        
        self.next_line()
        
    def next_line(self):
        self.line_num += 1
        self.token_num = -1

        if self.line_num >= len(self.lines):self.line = None

        else:
            self.line = self.lines[self.line_num]
            self.advance()

    def advance(self):
        if self.line == None:
            self.tok = None
            return
        
        self.token_num += 1
        self.idx += 1
        
        if self.token_num >= len(self.line): self.tok = None
        else: self.tok = self.line[self.token_num]

        self.pos = Position(self.idx, self.line_num, self.line_num, self.fn, self.lines)
        
    def parse(self):

        pos_start = self.pos.copy()

        if (self.tok == None) or (self.tok.type != TT_DIR) or (self.tok.value != 'section'):
            pos_start.ln = self.line_nums[pos_start.ln]
            return [], InvalidInstructionError(pos_start, self.pos, "First line must be a \'.section\' directive")

        self.advance()

        if (self.tok == None) or (self.tok.type != TT_STRING) or (self.tok.value not in ['.text', '.data']):
            pos_start.ln = self.line_nums[pos_start.ln]
            return [], InvalidInstructionError(pos_start, self.pos, "First line must be a \'.section .data\' or \'.section .text\' directive")

        if self.tok.value == '.data': self.section = '.data'
        else: self.section = '.text'

        self.next_line()

        self.instructions = []
        self.label_locations = {}
        self.data = []
        self.data_locations = {}
        
        while self.section == '.data':

            pos_start = self.pos
            # Move to text section if you find text
            if (self.tok.type == TT_DIR) and (self.tok.value == 'section') and (len(self.line) == 2):
                self.advance()
                if (self.tok.type == TT_STRING) and (self.tok.value == '.text'):
                    self.section = '.text'
                    break

            elif (self.tok.type == TT_LABEL):
                ret = self.data_label_parse()
                if ret != None:
                    return [], ret

            self.next_line()

        #### Saving these for resetting after counting labels
        text_begin_line = self.line_num
        text_begin_idx = self.idx
        
        self.next_line()
        
        ###### Finding the label locations
        inst_count = 0
        while self.line != None:
            pos_start = self.pos
            if self.tok.type == TT_LABEL:
                self.label_locations[self.tok.value] = inst_count
            elif self.tok.type == TT_INST:
                if self.tok.value in DOUBLE_LENGTH_INSTRUCTIONS:
                    inst_count += 1
                inst_count += 1
            elif self.tok.type == TT_DIR:
                if self.tok.value not in ['global', 'end']:
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return [], InvalidInstructionError(pos_start, self.pos, "'" + self.tok.value + "'")
            elif self.tok.type == TT_FNCT:
                pass
            else:
                pos_start.ln = self.line_nums[pos_start.ln]
                return [], InvalidInstructionError(pos_start, self.pos, "'" + self.tok.value + "'")


            self.next_line()

        # Reset back to .text section
        self.line_num = text_begin_line
        self.idx = text_begin_idx
        self.next_line()

        #### Parsing
        pc = 0
        while self.line != None:
            pos_start = self.pos.copy()
            if self.tok.type == TT_INST:
                add = False
                if self.tok.value in DOUBLE_LENGTH_INSTRUCTIONS:
                    add = True
                result = self.inst_parse(pc)
                if result != None:
                    return [], result
                if add:
                    self.instructions.append(None)
                    pc += 1
                pc += 1
            elif self.tok.type == TT_LABEL:
                pass
            elif self.tok.type == TT_DIR:
                if self.tok.value == 'end':
                    if (self.line_num != ( len(self.lines) - 1 )):
                        pos_start.ln = self.line_nums[pos_start.ln]
                        return [], InvalidInstructionError(pos_start, self.pos, ".end must be the last line of the file")
                elif self.tok.value == 'global':
                    if len(self.instructions) != 0:
                        pos_start.ln = self.line_nums[pos_start.ln]
                        return [], InvalidInstructionError(pos_start, self.pos, ".global must be the first line in the text section")
                    self.advance()
                    if not isinstance(self.tok, Token):
                        pos_start.ln = self.line_nums[pos_start.ln]
                        return [], InvalidInstructionError(pos_start, self.pos, ".global must have another argument")
                    if (self.tok.type != TT_STRING) or (self.tok.value not in self.label_locations):
                        pos_start.ln = self.line_nums[pos_start.ln]
                        return [], InvalidInstructionError(pos_start, self.pos, f'Cannot find label \'{self.tok.value}\' in this file')
                else:
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return [], InvalidInstructionError(pos_start, self.pos, f'\'{self.tok.value}\'')
            else:
                pos_start.ln = self.line_nums[pos_start.ln]
                return [], InvalidInstructionError(pos_start, self.pos, "'" + self.tok.value + "'")

            self.next_line()

        return [self.instructions, self.data], None

    def inst_parse(self, pc):

        pos_start = self.pos.copy()
        inst = self.tok.value
        reqs = INST_REQUIREMENTS[inst]
        req_len = len(reqs)
        idx = 0
        inst_info = [inst]
        self.advance()
        while (self.tok != None) and (reqs[0] != None):
            if idx >= req_len:
                pos_start.ln = self.line_nums[pos_start.ln]
                return InvalidInstructionError(pos_start, self.pos, "Too many arguments given")
            req = reqs[idx] # requirement
            if isinstance(req, list):
                if self.tok.type not in req: 
                    if self.tok.value != None:
                        pos_start.ln = self.line_nums[pos_start.ln]
                        return InvalidInstructionError(pos_start, self.pos, "Incorrect argument \'" + str(self.tok.value) + "\'")
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, "Incorrect argument \'" + str(self.tok.type) + "\'")
            elif self.tok.type != req: 
                if self.tok.value != None:
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, "Incorrect argument \'" + str(self.tok.value) + "\'")
                pos_start.ln = self.line_nums[pos_start.ln]
                return InvalidInstructionError(pos_start, self.pos, "Incorrect argument \'" + str(self.tok.type) + "\'")

            if self.tok.type != TT_COMMA: # add to instruction info if its not a comma
                if (self.tok.type == TT_STRING):
                    if (self.tok.value in self.label_locations):
                        if inst[:2].upper() in ['RC', 'RJ', 'BR']: 
                            k = self.label_locations[self.tok.value] - pc - 1
                            if inst[:2].upper == 'RC' and ( (k < -64) or (k > 63) ):
                                pos_start.ln = self.line_nums[pos_start.ln]
                                return InvalidInstructionError(pos_start, self.pos, "Label too far away to access from \'" + self.tok.value + "\'")
                            elif ( (k < -2048) or (k > 2047) ):
                                pos_start.ln = self.line_nums[pos_start.ln]
                                return InvalidInstructionError(pos_start, self.pos, "Label too far away to access from \'" + self.tok.value + "\'")
                            inst_info.append(k)
                        else: inst_info.append(self.label_locations[self.tok.value])

                    elif (self.tok.value in self.data_locations):
                        k = self.data_locations[self.tok.value]
                        if ( (k < 0) or (k > 65535) ):
                            pos_start.ln = self.line_nums[pos_start.ln]
                            return InvalidInstructionError(pos_start, self.pos, "\'" + self.tok.value + "\'")
                        inst_info.append(k)

                
                elif (self.tok.type in [TT_HI8, TT_LO8]):
                    loc = self.data_locations[self.tok.value]
                    if (self.tok.type == TT_HI8): inst_info.append(int((loc - (loc % 256)) / 256))
                    else: inst_info.append(loc % 256)
                
                elif (self.tok.value != None):
                    inst_info.append(self.tok.value)
                
                else: inst_info.append(self.tok.type)

            
            self.advance()
            idx += 1

        if (idx != req_len):
            if not ((reqs[0] == None) and (idx == 0)):
                pos_start.ln = self.line_nums[pos_start.ln]
                return InvalidInstructionError(pos_start, self.pos, "Not enough arguments given")

        self.instructions.append(inst_info)

    def data_label_parse(self):
        pos_start = self.pos.copy()

        lab = self.tok.value # label
        self.advance()
        if self.tok == None:
            pos_start.ln = self.line_nums[pos_start.ln]
            return InvalidInstructionError(pos_start, self.pos, "Not enough arguments given")

        if self.tok.type != TT_DIR:
            pos_start.ln = self.line_nums[pos_start.ln]
            return InvalidInstructionError(pos_start, self.pos, "'" + self.tok.value + "'")

        self.data_locations[lab] = len(self.data) # add lable to data locations

        if self.tok.value == 'byte':
            self.advance()
            int_ = True
            comma_ = False
            while self.tok != None:
                if (int_) and (self.tok.type != TT_INT):
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, "Expected integer, instead got \'" + self.tok.value + "'")
                elif (comma_) and (self.tok.type != TT_COMMA):
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, "Expected comma, instead got \'" + self.tok.value + "'")

                if int_:
                    self.data.append(int(self.tok.value))

                int_ = not int_
                comma_ = not comma_

                self.advance()
            if int_: # if you've just ended on a comma
                pos_start.ln = self.line_nums[pos_start.ln]
                return InvalidInstructionError(pos_start, self.pos, "Cannot end a line with a comma")

        elif self.tok.value == 'space':
            if len(self.line) not in [3, 5]:
                pos_start.ln = self.line_nums[pos_start.ln]
                return InvalidInstructionError(pos_start, self.pos, "The .space directive has an incorrect number of arguments")
            self.advance()
            if self.tok.type != TT_INT:
                pos_start.ln = self.line_nums[pos_start.ln]
                return InvalidInstructionError(pos_start, self.pos, "The .space directive needs an integer as an argument")
            
            
            num_spaces = int(self.tok.value)
            self.advance()
            val = 0
            if len(self.line) == 5:
                if self.tok.type != TT_COMMA:
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, "The .space directive needs a comma")
                self.advance()
                if self.tok.type != TT_INT:
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, "The .space directive needs an integer for both arguments")
                val = int(self.tok.value)
            
            for i in range(num_spaces):
                self.data.append(val)

        elif self.tok.value in ['string', 'ascii', 'asciz']:
            self.advance()
            while self.tok != None:
                if (self.tok == None):
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return  InvalidInstructionError(pos_start, self.pos, "Not enough arguments given")
                if self.tok.type not in [TT_STRING, TT_COMMA]:
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return  InvalidInstructionError(pos_start, self.pos, "'" + str(self.tok.value) + "'" + " is not a string")
                if self.tok.type == TT_STRING:
                    slash = False
                    for elem in self.tok.value:

                        if (elem == '\\') and (not slash):
                            slash = True
                        else:
                            if slash:
                                self.data.append(ord(BACKSLASH_VALS['\\' + elem]))
                            else:
                                self.data.append(ord(elem))
                            slash = False
                self.advance()
        elif self.tok.value in ['section', 'global', 'end']:
            pos_start.ln = self.line_nums[pos_start.ln]
            return InvalidInstructionError(pos_start, self.pos, f'\'.{self.tok.value}\' is not a valid directive after a label')




BACKSLASH_VALS = {
    '\\n': '\n',
    '\\\'': '\'',
    '\\\"': '\"',
    '\\t': '\t',
    '\\\\': '\\'
}

# Arguments for each inst
INST_REQUIREMENTS = {
    'ADC': [TT_REG, TT_COMMA, TT_REG],
    'ADD': [TT_REG, TT_COMMA, TT_REG],
    'AND': [TT_REG, TT_COMMA, TT_REG],
    'ANDI': [TT_REG, TT_COMMA, TT_INT],
    'BCLR': [TT_INT],
    'BRBC': [TT_INT, TT_COMMA, TT_STRING],
    'BRBS': [TT_INT, TT_COMMA, TT_STRING],
    'BRCC': [TT_STRING], 
    'BRCS': [TT_STRING],
    'BREQ': [TT_STRING],
    'BRGE': [TT_STRING],
    'BRHC': [TT_STRING],
    'BRHS': [TT_STRING],
    'BRID': [TT_STRING],
    'BRIE': [TT_STRING],
    'BRLO': [TT_STRING],
    'BRLT': [TT_STRING],
    'BRMI': [TT_STRING],
    'BRNE': [TT_STRING],
    'BRPL': [TT_STRING],
    'BRSH': [TT_STRING],
    'BRTC': [TT_STRING],
    'BRTS': [TT_STRING],
    'BRVC': [TT_STRING],
    'BRVS': [TT_STRING],
    'BSET': [TT_INT],
    'CALL': [[TT_STRING, TT_FNCT]],
    'CBI': [TT_INT, TT_COMMA, TT_INT],
    'CBR': [TT_REG, TT_COMMA, TT_INT],
    'CLC': [None],
    'CLH': [None],
    'CLI': [None],
    'CLN': [None],
    'CLR': [TT_REG],
    'CLS': [None],
    'CLT': [None],
    'CLV': [None],
    'CLZ': [None],
    'COM': [TT_REG],
    'CP': [TT_REG, TT_COMMA, TT_REG],
    'CPC': [TT_REG, TT_COMMA, TT_REG],
    'CPI': [TT_REG, TT_COMMA, TT_INT],
    'DEC': [TT_REG],
    'EOR': [TT_REG, TT_COMMA, TT_REG],
    'IN': [TT_REG, TT_COMMA, TT_INT],
    'INC': [TT_REG],
    'JMP': [TT_STRING],
    'LD': [TT_REG, TT_COMMA, [TT_X, TT_Y, TT_Z, TT_XP, TT_YP, TT_ZP, TT_MX, TT_MY, TT_MZ] ],
    'LDD': [TT_REG, TT_COMMA, [TT_XP, TT_YP, TT_ZP], TT_INT],
    'LDI': [TT_REG, TT_COMMA, [TT_INT, TT_LO8, TT_HI8]],
    'LDS': [TT_REG, TT_COMMA, [TT_STRING, TT_INT]],
    'LSL': [TT_REG],
    'LSR': [TT_REG],
    'MOV': [TT_REG, TT_COMMA, TT_REG],
    'MUL': [TT_REG, TT_COMMA, TT_REG],
    'MULS': [TT_REG, TT_COMMA, TT_REG],
    'MULSU': [TT_REG, TT_COMMA, TT_REG],
    'NEG': [TT_REG],
    'NOP': [None],
    'OR': [TT_REG, TT_COMMA, TT_REG],
    'ORI': [TT_REG, TT_COMMA, TT_INT],
    'OUT': [TT_INT, TT_COMMA, TT_REG],
    'POP': [TT_REG],
    'PUSH': [TT_REG],
    'RJMP': [TT_STRING],
    'RET': [None],
    'ROL': [TT_REG],
    'ROR': [TT_REG],
    'SBC': [TT_REG, TT_COMMA, TT_REG],
    'SBI': [TT_INT, TT_COMMA, TT_INT],
    'SBR': [TT_REG, TT_COMMA, TT_INT],
    'SEC': [None],
    'SEH': [None],
    'SEI': [None],
    'SEN': [None],
    'SER': [TT_REG],
    'SES': [None],
    'SET': [None],
    'SEV': [None],
    'SEZ': [None],
    'ST': [[TT_X, TT_Y, TT_Z, TT_XP, TT_YP, TT_ZP, TT_MX, TT_MY, TT_MZ], TT_COMMA, TT_REG],
    'STD': [[TT_XP, TT_YP, TT_ZP], TT_INT, TT_COMMA, TT_REG],
    'STS': [[TT_STRING, TT_INT], TT_COMMA, TT_REG],
    'SUB': [TT_REG, TT_COMMA, TT_REG],
    'SUBI': [TT_REG, TT_COMMA, TT_INT],
    'SWAP': [TT_REG],
    'XCH': [TT_Z, TT_COMMA, TT_REG]
}

# Is it a single word or double word instruction?
DOUBLE_LENGTH_INSTRUCTIONS = [
    'CALL',
    'JMP',
    'LDS',
    'STS'
]

##### Parser should
# Check all the lines are correct
# Do all the .data work
# Convert all of the labels to numbers
# Convert all the instructions with labels to numbers
# Convert all the instructions to instruction nodes
# Put all the instruction nodes in a list in order

