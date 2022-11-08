import sys

#path = sys.path
#sim_path = path[0] + '/lib'
#path.insert(1, sim_path)

#from avr_sim import * # import from avr_sim file in sim

import string
import copy
from tkinter import *
from tkinter.filedialog import askopenfilename

"""
To add a new instruction:
- Add to INST_LIST (in avr_lexer.py)
- Add to INST_REQUIREMENTS (in avr_parser.py)
- Add in INST_OPERANDS (in avr_parser.py)
- Add its execution info interpreter.step() method (in avr_interpreter.py)
- Add it's binary info to interpreter get_binary_instruction() method
- UDL on Notepadd++ ALREADY has all the instructions

To add a new directive:
- Add to DIRECTIVES list
- Add to Parser.data_label_parse() and Parser.parse() methods
"""

##################################################################################################################
#  ERROR
##################################################################################################################

class Error:
    def __init__(self, pos_start, pos_end, error_name, details):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.error_name = error_name
        self.details = details

    def as_string(self):
        result = f'{self.error_name}: {self.details}'
        result += f'\nFile {self.pos_start.fn}, line {self.pos_start.ln}'
        return result

    def __repr__(self):
        result = f'{self.error_name}: {self.details}'
        result += f'\nFile {self.pos_start.fn}, line {self.pos_start.ln}'
        return result

class IllegalCharError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Illegal Character', details)

class InvalidInstructionError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Invalid Instruction', details)

class UnexpectedValue(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Unexpected Value', details)

class RETError():  # Used for interpreter
    def __init__(self, pos, details):
        self.pos = pos
        self.details = details

    def __repr__(self):
        result = f'RET Error: {self.details}\nInstruction {self.pos}\n'
        return result

    def as_string(self):
        return self.__repr__()

class StackOverflowError():  # Used for interpreter
    def __init__(self, pos, details):
        self.pos = pos
        self.details = details

    def __repr__(self):
        result = f'Stack Overflow Error: {self.details}\nInstruction {self.pos}\n'
        return result

    def as_string(self):
        return self.__repr__()
        
##################################################################################################################
#  POSITION
##################################################################################################################

class Position:
    def __init__(self, idx, ln, col, fn, ftxt):
        self.idx = idx # index
        self.ln = ln # line number
        self.col = col # column
        self.fn = fn # file name
        self.fxtx = ftxt # file text

    def __repr__(self):
        return f'Line {self.ln}, column {self.col} in file: {self.fn}'

    def advance(self, current_char):
        self.idx += 1
        self.col += 1

        if current_char == '\n':
            self.ln += 1
            self.col = 0
    
    def copy(self):
        return Position(self.idx, self.ln, self.col, self.fn, self.fxtx)


##################################################################################################################
#  TOKEN
##################################################################################################################

class Token:
    def __init__(self, type_, value=None):
        self.type = type_
        self.value = value

    def __repr__(self):
        if self.value: return f'{self.type}:{self.value}'
        return f'{self.type}'



##################################################################################################################
#  REGISTER
##################################################################################################################

class Register:
    def __init__(self, name, value=0, changed=0):
        self.name = str(name) # eg 3 for R3
        self.value = value
        self.changed = changed # for displaying as red when the value is updated

    def __repr__(self):
        return f'{self.name}: {self.value}'

    def as_string(self):
        return f'{self.name}: {self.value}'

    def new_instruct(self):
        self.changed = 0

    def set_value(self, new_value):
        self.value = new_value % 256
        self.changed = 1

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



##################################################################################################################
#  LEXER
##################################################################################################################

class Lexer:
    def __init__(self, fn, text):
        self.fn = fn # file name
        self.text = text
        self.pos = Position(-1, 1, -1, fn, text)
        self.current_char = None 

        self.advance()

    def advance(self):
        self.pos.advance(self.current_char)
        self.current_char = self.text[self.pos.idx] if self.pos.idx < len(self.text) else None

    def make_tokens(self):
        lines = []
        tokens = []
        directive = None
        line_nums = [] # line that each tokens list is on in the original file

        while self.current_char != None:

            if self.current_char in [' ', '\t']:
                self.advance()
            elif self.current_char == '\n':
                if len(tokens) > 0:
                    lines.append(tokens)
                    tokens = []
                    line_nums.append(self.pos.ln)
                self.advance()
                directive = None
            elif self.current_char == ';':
                self.skip_comments()
            elif self.current_char == ',':
                tokens.append(Token(TT_COMMA))
                self.advance()
            elif self.current_char == '\"':
                tokens.append(self.make_string(directive))
                self.advance()
            elif (len(tokens) > 0) and (self.current_char in 'XYZ'):
                tok = self.make_XYZ()
                if not isinstance(tok, Token): return [], tok
                tokens.append(tok) # dont advance after because it does in the method
            elif self.current_char in (LETTERS + '._'):
                if len(tokens) > 0: tok = self.make_InstRegLabelStrDir(directive, tokens[-1])
                else: tok = self.make_InstRegLabelStrDir(directive)
                if not isinstance(tok, Token): return [], tok
                tokens.append(tok) # dont advance after because it does in the method
                if (tok.type == TT_DIR) and (tok.value in ['string', 'asciz']):
                    directive = tok.value
            elif self.current_char == '+':
                tokens.append(Token(TT_PLUS))
                self.advance()
            elif self.current_char == '-':
                tok = self.make_XYZ()
                if not isinstance(tok, Token): return [], tok
                tokens.append(tok)
            elif self.current_char in DIGITS:
                tokens.append(self.make_number()) # dont advance after because it already does in the method
            elif self.current_char == '=':
                tokens.append(Token(TT_EQ))
                self.advance()
            else:
                pos_start = self.pos.copy()
                char = self.current_char
                self.advance()
                return [], IllegalCharError(pos_start, self.pos, "'" + char + "'")


        if len(tokens) > 0: lines.append(tokens)
        lines.append(line_nums) # adding the line numbers to the end of the list to be taken off and used

        return lines, None

    def make_number(self):
        num_str = ''
        other_base = False # if the number is in another base such as hex or binary, continue
        base = 10 # assume base == 10 unless otherwise

        base_signifiers = {'b': 2, 'o': 8, 'x': 16} # tells what base the number is in
        
        while ( self.current_char not in [None, '\n', ' ', ',', ';']) and ( self.current_char in DIGITS or other_base ):
            num_str += self.current_char
            self.advance()
            
            #########################
            # For dealing with other bases

            if (num_str == '0') and (self.current_char in base_signifiers):
                other_base = True
                base = base_signifiers[self.current_char]



            #########################
        if base != 10: number = int(num_str[2:], base)
        else: number = int(num_str)

        number = number % 256
        
        return Token(TT_INT, number)

    def make_directive(self):
        """
        Makes section token
        """
        pos_start = self.pos.copy()
        dir_str = ''

        while (self.current_char != None) and (self.current_char != '\n') and (self.current_char in (LETTERS + '.')):
            dir_str += self.current_char
            self.advance()

        if dir_str in DIRECTIVES:
            dir_ = dir_str.split('.')[-1] # directive type
            return Token(TT_DIR, dir_)
        
        return InvalidInstructionError(pos_start, self.pos, "'" + dir_str + "'")

    def make_string(self, directive=None):
        pos_start = self.pos.copy()
        char = self.current_char
        if char != '\"': return IllegalCharError(pos_start, self.pos, '"' + self.current_char + '"')
        self.advance()

        slash = False
        str_string = ''
        while (self.current_char != '\"') or slash:
            if self.current_char in ['\n', None]: return InvalidInstructionError(pos_start, self.pos, '"' + str_string + '"')
            str_string += self.current_char
            if self.current_char == '\\':
                slash = (not slash)
            else: slash = False
            self.advance()

        if (directive != None) and (directive in ['string', 'asciz']):
            str_string += chr(0x00) # += NULL

        return Token(TT_STRING, str_string)

    def make_XYZ(self):
        pos_start = self.pos.copy()
        char_str = ''

        while self.current_char in ['X', 'Y', 'Z', '-', '+', ' ']:
            if self.current_char != ' ': char_str += self.current_char
            self.advance()
        
        if (self.current_char in DIGITS) and (char_str == '-'):
            tok = self.make_number()
            tok.value = (-1 * tok.value) % 256
            return tok

        XYZ_dict = {
            'X': TT_X,
            'Y': TT_Y,
            'Z': TT_Z,
            'X+': TT_XP,
            '-X': TT_MX,
            'Y+': TT_YP,
            '-Y': TT_MY,
            'Z+': TT_ZP,
            '-Z': TT_MZ,
        }

        if char_str in XYZ_dict: return Token(XYZ_dict[char_str])

        else: return InvalidInstructionError(pos_start, self.pos, "'" + char_str + "'")

    def make_InstRegLabelStrDir(self, directive=None, last_tok=None):
        """
        Makes instruction token or
        register token or label token.
        """
        pos_start = self.pos.copy()
        id_str = self.make_id_str()

        if self.current_char == ':': # important if statement
            self.advance()

            if isinstance(last_tok, Token) and (last_tok.type in [TT_INST, TT_COMMA]): # for double register tokenizing
                id_str = id_str + ':' + self.make_id_str()
                return Token(TT_REG, id_str.upper())

            return Token(TT_LABEL, id_str)
        
        elif id_str.upper() in INST_LIST:
            return Token(TT_INST, id_str.upper())
            
        elif id_str.upper() in REGISTER_FILE:
            return Token(TT_REG, id_str.upper())

        elif id_str in DIRECTIVES:
            return Token(TT_DIR, id_str[1:])

        elif id_str.upper() in FUNCTIONS:
            return Token(TT_FNCT, id_str.upper())

        elif (len(id_str) > 5) and (id_str[-1] == ')'):
            if (id_str[:4].lower() == 'lo8('):
                return Token(TT_LO8, id_str[4:len(id_str) - 1])
            
            elif (id_str[:4].lower() == 'hi8('):
                return Token(TT_HI8, id_str[4:len(id_str) - 1])

        else:
            if directive in ['string', 'asciz']:
                id_str += chr(0x00) # += NULL
            return Token(TT_STRING, id_str)

        #return InvalidInstructionError(pos_start, self.pos, "'" + id_str + "'")

    def make_id_str(self):
        id_str = ''
        while (self.current_char != None) and (self.current_char != '\n') and (self.current_char in (LETTERS + DIGITS + '._()')):
            id_str += self.current_char
            self.advance()

        return id_str

    def skip_comments(self):

        while self.current_char not in [None, '\n']:
            self.advance()



######################################
#  CHARACTERS
######################################

DIGITS = '0123456789'
LETTERS = string.ascii_letters # lower case & upper case


######################################
#  INSTRUCTIONS
######################################

INST_LIST = [
    'ADC',
    'ADD',
    'ADIW',
    'AND',
    'ANDI',
    'ASR',
    'BCLR',
    'BRBC',
    'BRBS',
    'BRCC',
    'BRCS',
    'BREQ',
    'BRGE',
    'BRHC',
    'BRHS',
    'BRID',
    'BRIE',
    'BRLO',
    'BRLT',
    'BRMI',
    'BRNE',
    'BRPL',
    'BRSH',
    'BRTC',
    'BRTS',
    'BRVC',
    'BRVS',
    'BSET',
    'CALL',
    'CBI',
    'CBR',
    'CLC',
    'CLH',
    'CLI',
    'CLN',
    'CLR',
    'CLS',
    'CLT',
    'CLV',
    'CLZ',
    'COM',
    'CP',
    'CPC',
    'CPI',
    'DEC',
    'EOR',
    'IN',
    'INC',
    'JMP',
    'LD',
    'LDD',
    'LDI',
    'LDS',
    'LSL',
    'LSR',
    'MOV',
    'MOVW',
    'MUL',
    'MULS',
    'MULSU',
    'NEG',
    'NOP',
    'OR',
    'ORI',
    'OUT',
    'POP',
    'PUSH',
    'RJMP',
    'RET',
    'ROL',
    'ROR',
    'SBC',
    'SBI',
    'SBIW',
    'SBR',
    'SBRC',
    'SBRS',
    'SEC',
    'SEH',
    'SEI',
    'SEN',
    'SER',
    'SES',
    'SET',
    'SEV',
    'SEZ',
    'ST',
    'STD',
    'STS',
    'SUB',
    'SUBI',
    'SWAP',
    'TST',
    'XCH'
]   

######################################
#  BUILT IN FUNCTIONS
######################################

FUNCTIONS = [
    "PRINTF"
]

######################################
#  TOKENS
######################################

TT_INST = 'INST' # instruction
TT_INT = 'INT' # integer
TT_REG = 'REG' # register
TT_COMMA = 'COMMA'
TT_LABEL = 'LABEL' # label (e.g start:)
TT_DIR = 'DIR' # directive (e.g .section, .byte .....)
TT_PLUS = 'PLUS'
TT_MINUS = 'MINUS'
TT_EQ = 'EQUALS'
TT_X = 'X'
TT_XP = 'X+'
TT_MX = '-X'
TT_Y = 'Y'
TT_YP = 'Y+'
TT_MY = '-Y'
TT_Z = 'Z'
TT_ZP = 'Z+'
TT_MZ = '-Z'
TT_STRING = 'STR' # string
TT_QUOTE = 'QUOTE' # "
TT_LO8 = 'LO8' # lo8 function
TT_HI8 = 'HI8' # hi8 function
TT_FNCT = 'FNCT' # inbuilt function

DIRECTIVES = [
    '.section',
    '.end',
    '.global',
    '.byte',
    '.string',
    '.ascii',
    '.asciz',
    '.space',
    '.def'
]


##################################################################################################################
#  PARSER
##################################################################################################################


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
        self.definitions = {}
        
        ###### Parsing data section
        while self.section == '.data':

            pos_start = self.pos
            # Move to text section if you find text
            if (self.tok.type == TT_DIR) and (self.tok.value == 'section') and (len(self.line) == 2):
                self.advance()
                if (self.tok.type == TT_STRING) and (self.tok.value == '.text'):
                    self.section = '.text'
                    break

            elif (self.tok.type == TT_LABEL) or (self.tok.type == TT_DIR):
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
                if len(self.line) > 1:
                    self.advance()
                    if self.tok.value in DOUBLE_LENGTH_INSTRUCTIONS:
                        inst_count += 1
                    inst_count += 1
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

        ### Sub in defined variables

        #### Parsing instruction section
        pc = 0
        while self.line != None:
            pos_start = self.pos.copy()
            if (self.tok.type == TT_LABEL) and (len(self.line) > 1): # if there is an instruction in the line
                self.advance()
            
            if self.tok.type == TT_INST:

                # Convert definitions to registers
                for i in range(len(self.line)):
                    if self.line[i].value in self.definitions:
                        reg = self.definitions[self.line[i].value]
                        self.line[i] = Token(TT_REG, reg.upper())
                
                result = self.inst_parse(pc)
                
                if result != None: return [], result
                
                if self.instructions[-1] == None:
                    result = self.check_operands(-2) # check for out of bounds operands
                    pc += 1
                else:
                    result = self.check_operands(-1) # check for out of bounds operands

                if result != None: return [], result

                pc += 1


            elif self.tok.type == TT_LABEL:
                if len(self.line) > 1:
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return [], InvalidInstructionError(pos_start, self.pos, "'" + self.tok.value + "'")
            
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

        if self.lines[-1][0].value != 'end':    # check file ends in ".end" 
            pos_start.ln = self.line_nums[-1]
            return [], InvalidInstructionError(pos_start, self.pos, ".end must be the last line of the file")

        return [self.instructions, self.data], None

    def inst_parse(self, pc):
        """
        Takes a line of code, parses
        all the tokens, and confirms they
        are valid.
        """

        pos_start = self.pos.copy()
        inst = self.tok.value
        reqs = INST_REQUIREMENTS[inst]
        req_len = len(reqs)
        idx = 0
        inst_info = [inst]
        self.advance()
        while (self.tok != None):

            if idx >= req_len: # if instruction has too many arguments
                pos_start.ln = self.line_nums[pos_start.ln]
                return InvalidInstructionError(pos_start, self.pos, "Too many arguments given")
            
            req = reqs[idx] # requirement up to
            if isinstance(req, list): # if requirement has options
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
            
            if (self.tok.type == TT_STRING): # if it's a label or data value
                
                if (self.tok.value in self.label_locations): # for labels
                    if inst[:2].upper() in ['RC', 'RJ', 'BR']: # if branch, rcall or rjump (has a set range of jumping)
                        k = self.label_locations[self.tok.value] - pc - 1
                        if inst[:2].upper == 'BR' and ( (k < -64) or (k > 63) ):
                            pos_start.ln = self.line_nums[pos_start.ln]
                            return InvalidInstructionError(pos_start, self.pos, "Label too far away to access from \'" + self.tok.value + "\'")
                        elif ( (k < -2048) or (k > 2047) ):
                            pos_start.ln = self.line_nums[pos_start.ln]
                            return InvalidInstructionError(pos_start, self.pos, "Label too far away to access from \'" + self.tok.value + "\'")
                        inst_info.append(k)

                    else: inst_info.append(self.label_locations[self.tok.value]) # add the label location instead of the name

                elif (self.tok.value in self.data_locations): # for RAM variables
                    k = self.data_locations[self.tok.value]
                    if ( (k < 0) or (k > 65535) ):
                        pos_start.ln = self.line_nums[pos_start.ln]
                        return InvalidInstructionError(pos_start, self.pos, "\'" + self.tok.value + "\'")
                    inst_info.append(k)

                else:
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, f"Illegal argument given: {self.tok.value}")
                
            elif (self.tok.type in [TT_HI8, TT_LO8]):
                loc = self.data_locations[self.tok.value]
                if (self.tok.type == TT_HI8): inst_info.append(int((loc - (loc % 256)) / 256))
                else: inst_info.append(loc % 256)
                
            
            elif (self.tok.value != None):
                inst_info.append(self.tok.value)
                
            elif (self.tok.type != TT_COMMA): inst_info.append(self.tok.type) # don't add commas
            
            self.advance()
            idx += 1

        if reqs[0] == None: idx += 1

        if (idx < req_len): # if not enough arguments given in the instruction
            pos_start.ln = self.line_nums[pos_start.ln]
            return InvalidInstructionError(pos_start, self.pos, "Not enough arguments given")

        self.instructions.append(inst_info)
        if inst in DOUBLE_LENGTH_INSTRUCTIONS:
            self.instructions.append(None)
        
    def data_label_parse(self):
        pos_start = self.pos.copy()

        lab = self.tok.value # label
        lab_type = self.tok.type

        if lab_type == TT_LABEL:
            self.advance()
        
        if self.tok == None:
            pos_start.ln = self.line_nums[pos_start.ln]
            return InvalidInstructionError(pos_start, self.pos, "Not enough arguments given")

        if (self.tok.type != TT_DIR):
            pos_start.ln = self.line_nums[pos_start.ln]
            return InvalidInstructionError(pos_start, self.pos, "'" + self.tok.value + "'")

        self.data_locations[lab] = len(self.data) + 0x100 # add lable to data locations

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
                    #val = int(self.tok.value) % 256
                    #if not 0 <= int(self.tok.value) <= 255:
                    #    pos_start.ln = self.line_nums[pos_start.ln]
                    #    return InvalidInstructionError(pos_start, self.pos, "RAM cells cannot store a number outside of the range: 0 - 255")
                
                    self.data.append(int(self.tok.value) % 256)

                int_ = not int_
                comma_ = not comma_

                self.advance()
            if int_: # if you've just ended on a comma
                pos_start.ln = self.line_nums[pos_start.ln]
                return InvalidInstructionError(pos_start, self.pos, "Cannot end a line with a comma")

        elif self.tok.value == 'space':
            if not (1 < len(self.line) < 6):
                pos_start.ln = self.line_nums[pos_start.ln]
                return InvalidInstructionError(pos_start, self.pos, "The .space directive has an incorrect number of arguments")
            
            self.advance()
            if self.tok.type != TT_INT:
                pos_start.ln = self.line_nums[pos_start.ln]
                return InvalidInstructionError(pos_start, self.pos, "The .space directive needs an integer as an argument")
            
            num_spaces = int(self.tok.value)
            self.advance()
            val = 0
            if len(self.line) in [4, 5]:
                if self.tok.type != TT_COMMA:
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, "The .space directive needs a comma")
                self.advance()
                if self.tok.type != TT_INT:
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, "The .space directive needs an integer for both arguments")
                val = int(self.tok.value)

                if not 0 <= val <= 255:
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, "RAM cells cannot store a number outside of the range: 0 - 255")
                
            
            for i in range(num_spaces):
                self.data.append(val)

        elif self.tok.value in ['string', 'ascii', 'asciz']:
            self.advance()
            while self.tok != None:
                if (self.tok == None):
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, "Not enough arguments given")
                if self.tok.type not in [TT_STRING, TT_COMMA]:
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, "'" + str(self.tok.value) + "'" + " is not a string")
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

        elif self.tok.value == 'def':  # if the initial is a .def

            if len(self.line) != 4:
                pos_start.ln = self.line_nums[pos_start.ln]
                return InvalidInstructionError(pos_start, self.pos, f'Incorrect number of arguments given')
            
            self.advance()

            variable = self.tok.value

            if self.tok.type != TT_STRING:
                pos_start.ln = self.line_nums[pos_start.ln]
                return InvalidInstructionError(pos_start, self.pos, f'Illegal variable name \'{self.tok.value}\'')
            
            self.advance()
            if self.tok.type != TT_EQ:
                pos_start.ln = self.line_nums[pos_start.ln]
                return InvalidInstructionError(pos_start, self.pos, 'Must have an equals sign following a variable name')
            
            self.advance()

            if self.tok.type != TT_REG:
                pos_start.ln = self.line_nums[pos_start.ln]
                return InvalidInstructionError(pos_start, self.pos, 'Must set variable name to a register')

            self.definitions[variable] = self.tok.value # setting a variable name for a register
                
        elif self.tok.value in ['section', 'global', 'end']:
            pos_start.ln = self.line_nums[pos_start.ln]
            return InvalidInstructionError(pos_start, self.pos, f'\'.{self.tok.value}\' is not a valid directive in the data section.')

    def check_operands(self, idx):

        inst = self.instructions[idx]
        
        if len(inst) == 1:
            return
        
        ops = inst[1:]
        requirements = INST_OPERANDS[inst[0]]

        pos_start = self.pos.copy()

        for i in range(len(requirements)):
            req = requirements[i]

            if (req == None) or ((inst[0] == 'CALL') and (inst[1] in FUNCTIONS)):
                continue # skip this req
            
            if req[0] == 'd':
                d = int(ops[i].split('R')[-1])
                
                if ( not isinstance(req[1], list) ): # check d is within the bounds
                    if (d < req[1]) or (d > req[2]):
                        pos_start.ln = self.line_nums[pos_start.ln]
                        return InvalidInstructionError(pos_start, self.pos, f'Register \'{ops[i]}\' not allowed for {inst[0]}')

                elif ':' in ops[i]: # check for double register instructions
                    d_plus1 = int(ops[i].split('R')[-2].rstrip(':')) # big end register number
                    
                    if (d not in req[1]) or (d + 1 != d_plus1):
                        pos_start.ln = self.line_nums[pos_start.ln]
                        return InvalidInstructionError(pos_start, self.pos, f'Register \'{ops[i]}\' not allowed for {inst[0]}')

                    self.instructions[idx][i+1] = f'R{d}'


            elif req[0] == 'r':
                r = int(ops[i].split('R')[-1])
                
                if ( not isinstance(req[1], list) ): # check d is within the bounds
                    if (r < req[1]) or (r > req[2]):
                        pos_start.ln = self.line_nums[pos_start.ln]
                        return InvalidInstructionError(pos_start, self.pos, f'Register \'{ops[i]}\' not allowed for {inst[0]}')

                elif ':' in ops[i]: # check for double register instructions
                    r_plus1 = int(ops[i].split('R')[-2].rstrip(':')) # big end register number

                    if (r not in req[1]) or (r + 1 != r_plus1):
                        pos_start.ln = self.line_nums[pos_start.ln]
                        return InvalidInstructionError(pos_start, self.pos, f'Register \'{ops[i]}\' not allowed for {inst[0]}')

                    self.instructions[idx][i+1] = f'R{r}'

            elif req[0] == 'K':
                K = int(ops[i])
                
                if (K < req[1]) or (K > req[2]):
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, f'Immediate value \'{ops[i]}\' out of bounds for {inst[0]}')

            elif req[0] == 'k':
                k = int(ops[i])
                
                if (k < req[1]) or (k > req[2]):
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, f'Address value \'{ops[i]}\' out of bounds for {inst[0]}')

            elif req[0] == 'q':
                q = int(ops[i])
                 
                if (q < req[1]) or (q > req[2]):
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, f'Offset \'{ops[i]}\' out of bounds for {inst[0]}')

            elif req[0] == 'A':
                A = int(ops[i])
                 
                if (A < req[1]) or (A > req[2]):
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, f'I/O address \'{ops[i]}\' out of bounds for {inst[0]}')

            elif req[0] == 'b':
                b = int(ops[i])
                 
                if (b < req[1]) or (b > req[2]):
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, f'Bit \'{ops[i]}\' out of bounds for {inst[0]}')

            elif req[0] == 's':
                s = int(ops[i])
                 
                if (s < req[1]) or (s > req[2]):
                    pos_start.ln = self.line_nums[pos_start.ln]
                    return InvalidInstructionError(pos_start, self.pos, f'Bit \'{ops[i]}\' out of bounds for {inst[0]}')


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
    'ADIW': [TT_REG, TT_COMMA, TT_INT],
    'AND': [TT_REG, TT_COMMA, TT_REG],
    'ANDI': [TT_REG, TT_COMMA, TT_INT],
    'ASR': [TT_REG],
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
    'CALL': [[TT_STRING, TT_FNCT]],     # note: str,fnct is a list in a list, so it is optional to be str or fnct
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
    'LDD': [TT_REG, TT_COMMA, [TT_YP, TT_ZP], TT_INT],
    'LDI': [TT_REG, TT_COMMA, [TT_INT, TT_LO8, TT_HI8]],
    'LDS': [TT_REG, TT_COMMA, [TT_STRING, TT_INT]],
    'LSL': [TT_REG],
    'LSR': [TT_REG],
    'MOV': [TT_REG, TT_COMMA, TT_REG],
    'MOVW': [TT_REG, TT_COMMA, TT_REG],
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
    'SBIW': [TT_REG, TT_COMMA, TT_INT],
    'SBR': [TT_REG, TT_COMMA, TT_INT],
    'SBRC': [TT_REG, TT_COMMA, TT_INT],
    'SBRS': [TT_REG, TT_COMMA, TT_INT],
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
    'STD': [[TT_YP, TT_ZP], TT_INT, TT_COMMA, TT_REG],
    'STS': [[TT_STRING, TT_INT], TT_COMMA, TT_REG],
    'SUB': [TT_REG, TT_COMMA, TT_REG],
    'SUBI': [TT_REG, TT_COMMA, TT_INT],
    'SWAP': [TT_REG],
    'TST': [TT_REG],
    'XCH': [TT_Z, TT_COMMA, TT_REG]
}

# Allows ranges for each inst
INST_OPERANDS = {
    'ADC': [['d', 0, 31], ['r', 0, 31]],
    'ADD': [['d', 0, 31], ['r', 0, 31]],
    'ADIW': [['d', [24, 26, 28, 30]], ['K', 0, 63]],
    'AND': [['d', 0, 31], ['r', 0, 31]],
    'ANDI': [['d', 16, 31], ['K', 0, 255]],
    'ASR': [['d', 0, 31]],
    'BCLR': [['s', 0, 7]],
    'BRBC': [['s', 0, 7], ['k', -64, 63]],
    'BRBS': [['s', 0, 7], ['k', -64, 63]],
    'BRCC': [['k', -64, 63]], 
    'BRCS': [['k', -64, 63]],
    'BREQ': [['k', -64, 63]],
    'BRGE': [['k', -64, 63]],
    'BRHC': [['k', -64, 63]],
    'BRHS': [['k', -64, 63]],
    'BRID': [['k', -64, 63]],
    'BRIE': [['k', -64, 63]],
    'BRLO': [['k', -64, 63]],
    'BRLT': [['k', -64, 63]],
    'BRMI': [['k', -64, 63]],
    'BRNE': [['k', -64, 63]],
    'BRPL': [['k', -64, 63]],
    'BRSH': [['k', -64, 63]],
    'BRTC': [['k', -64, 63]],
    'BRTS': [['k', -64, 63]],
    'BRVC': [['k', -64, 63]],
    'BRVS': [['k', -64, 63]],
    'BSET': [['s', 0, 7]],
    'CALL': [['k', 0, 4194303]],
    'CBI': [['A', 0, 31], ['b', 0, 7]],
    'CBR': [['d', 16, 31], ['K', 0, 255]],
    'CLC': [None],
    'CLH': [None],
    'CLI': [None],
    'CLN': [None],
    'CLR': [['d', 0, 31]],
    'CLS': [None],
    'CLT': [None],
    'CLV': [None],
    'CLZ': [None],
    'COM': [['d', 0, 31]],
    'CP': [['d', 0, 31], ['r', 0, 31]],
    'CPC': [['d', 0, 31], ['r', 0, 31]],
    'CPI': [['d', 16, 31], ['K', 0, 255]],
    'DEC': [['d', 0, 31]],
    'EOR': [['d', 0, 31], ['r', 0, 31]],
    'IN': [['d', 0, 31], ['A', 0, 63]],
    'INC': [['d', 0, 31]],
    'JMP': [['k', 0, 4194303]],
    'LD': [['d', 0, 31]],
    'LDD': [['d', 0, 31], [None], ['q', 0, 63]],
    'LDI': [['d', 16, 31], ['K', 0, 255]],
    'LDS': [['d', 0, 31], ['k', 256, 65535]],
    'LSL': [['d', 0, 31]],
    'LSR': [['d', 0, 31]],
    'MOV': [['d', 0, 31], ['r', 0, 31]],
    'MOVW': [['d', [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]], ['r', [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]]],
    'MUL': [['d', 0, 31], ['r', 0, 31]],
    'MULS': [['d', 16, 31], ['r', 16, 31]],
    'MULSU': [['d', 16, 23], ['r', 16, 23]],
    'NEG': [['d', 0, 31]],
    'NOP': [None],
    'OR': [['d', 0, 31], ['r', 0, 31]],
    'ORI': [['d', 16, 31], ['K', 0, 255]],
    'OUT': [['A', 0, 63], ['r', 0, 31]],
    'POP': [['d', 0, 31]],
    'PUSH': [['d', 0, 31]],
    'RET': [None],
    'RJMP': [['k', -2048, 2047]],
    'ROL': [['d', 0, 31]],
    'ROR': [['d', 0, 31]],
    'SBC': [['d', 0, 31], ['r', 0, 31]],
    'SBI': [['A', 0, 31], ['b', 0, 7]],
    'SBIW': [['d', [24, 26, 28, 30]], ['K', 0, 63]],
    'SBR': [['d', 16, 31], ['K', 0, 255]],
    'SBRC': [['r', 0, 31], ['b', 0, 7]],
    'SBRS': [['r', 0, 31], ['b', 0, 7]],
    'SEC': [None],
    'SEH': [None],
    'SEI': [None],
    'SEN': [None],
    'SER': [['d', 0, 31]],
    'SES': [None],
    'SET': [None],
    'SEV': [None],
    'SEZ': [None],
    'ST': [[None], ['r', 0, 31]],
    'STD': [[None], ['q', 0, 63], ['r', 0, 31]],
    'STS': [['k', 256, 65535], ['r', 0, 31]],
    'SUB': [['d', 0, 31], ['r', 0, 31]],
    'SUBI': [['d', 16, 31], ['K', 0, 255]],
    'SWAP': [['d', 0, 31]],
    'TST': [['d', 0, 31]],
    'XCH': [[None], ['d', 0, 31]]
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


##################################################################################################################
#  INTERPRETER
##################################################################################################################


class Interpreter:
    def __init__(self, dmem, pmem, fn, inst_length):
        self.dmem = dmem
        self.pmem = pmem
        self.fn = fn
        self.pos = Position(-1, 0, -1, fn, self.pmem)
        self.inst_length = inst_length # number of instructions before all NOPs
        self.file_end = False # have you executed the whole file

        #self.pcl = self.dmem[0x5B] # PC low
        #self.pch = self.dmem[0x5C] # PC high

        self.pcl = Register('PCL')
        self.pch = Register('PCH')

        self.last_pc = 'N/A'

        self.sreg = self.dmem[0x5F]
        self.sph = self.dmem[0x5E]
        self.spl = self.dmem[0x5D]

        self.current_inst = self.pmem[self.get_pc_val()]

        self.pmem_length = len(self.pmem)
        self.dmem_length = len(self.dmem)

        #self.pushpop = 0 # counting (pushes - pops) for each subroutine layer

    def copy(self):
        return Interpreter(self.dmem, self.pmem, self.fn, self.inst_length)

    def step(self):
        if (not self.file_end) and (self.get_pc_val() < self.pmem_length):
            # Executes instruction and updates PC and SREG
            self.current_inst = self.pmem[self.get_pc_val()] # set current instruction
            inst = self.current_inst[0] # set instruction name
            self.last_pc = self.get_pc_val()

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

        elif inst == 'ADIW':
            Rdl = self.dmem[int(self.current_inst[1][1:])].value
            Rdh = self.dmem[int(self.current_inst[1][1:]) + 1].value
            K = int(self.current_inst[2])

            R = (256 * Rdh) + Rdl
            R = (R + K) % (256 * 256)
            RLow = R % 256
            RHigh = int((R - RLow)/256)

            self.dmem[int(self.current_inst[1][1:])].set_value(RLow)
            self.dmem[int(self.current_inst[1][1:]) + 1].set_value(RHigh)
            self.update_pc_val(self.get_pc_val() + 1)

            Rdh = self.make_8_bit_binary(Rdh)
            Rdl = self.make_8_bit_binary(Rdl)
            R = self.make_n_bit_binary(R, 16)

            self.sreg.value[5] = int(R[0])
            self.sreg.value[6] = int(R == '0000000000000000')
            self.sreg.value[4] = int(R[0]) & (1 - int(Rdh[0]))
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[7] = (1- int(R[0])) & int(Rdh[0])

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

        elif inst == 'ASR':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            R = self.make_8_bit_binary(Rd)
            C = int(R[7])
            R = R[0] + R[0:7]

            self.dmem[int(self.current_inst[1][1:])].set_value(int(R, 2))
            self.update_pc_val(self.get_pc_val() + 1)

            self.sreg.value[5] = int(R[0])
            self.sreg.value[4] = int(R[0]) ^ C
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')
            self.sreg.value[7] = C

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
                self.dmem[self.get_SP()] = self.pcl.value # adding to stack
                self.decrement_SP()
                self.dmem[self.get_SP()] = self.pch.value # adding to stack
                self.decrement_SP()
                k = int(self.current_inst[1])
                self.update_pc_val(k)

            elif self.current_inst[1] == 'PRINTF':
                ### Pop
                self.increment_SP()
                self.dmem[26].set_value(self.dmem[self.get_SP()] ) # R26 = lo8()

                self.increment_SP()
                self.dmem[27].set_value(self.dmem[self.get_SP()]) # R27 = hi8()

                ### Print
                printed_string = ''
                while True:
                    XYZ = 'X+'
                    val = self.get_XYZ(XYZ) # dmem value in XYZ
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
                self.dmem[self.get_SP()] = Rr
                self.decrement_SP()
                #self.dmem[27].set_value(Xhigh) # reset the value of R27 to what it was so it isnt disturbed

                Rr = self.dmem[26].value
                self.dmem[self.get_SP()] = Rr
                self.decrement_SP()
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
            val = self.get_XYZ(XYZ) # dmem value in XYZ
            K = self.dmem[val]
            self.dmem[int(self.current_inst[1][1:])].set_value(K)
            self.update_pc_val(self.get_pc_val() + 1)
            self.increment_XYZ(XYZ) # increments XYZ if necessary
        
        elif inst == 'LDD':
            XYZ = self.current_inst[2]
            q = int(self.current_inst[3])
            val = self.get_XYZ(XYZ) + q # dmem value in XYZ
            K = self.dmem[val]
            self.dmem[int(self.current_inst[1][1:])].set_value(K)
            self.update_pc_val(self.get_pc_val() + 1)
        
        elif inst == 'LDI':
            K = int(self.current_inst[2])
            self.dmem[int(self.current_inst[1][1:])].set_value(K)
            self.update_pc_val(self.get_pc_val() + 1)
        
        elif inst == 'LDS':
            k = self.dmem[int(self.current_inst[2])]
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

        elif inst == 'MOVW':
            d = int(self.current_inst[1][1:])
            r = int(self.current_inst[2][1:])
            Rrl = self.dmem[r].value
            Rrh = self.dmem[r + 1].value

            self.dmem[d].set_value(Rrl)
            self.dmem[d + 1].set_value(Rrh)
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
            A = int(self.current_inst[1])
            self.dmem[A + 0x20].set_value(Rd)
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'POP':

            if self.get_SP() < DMEM_MAX: # check if the top layer has no elements left (ie nothing left in stack)
                self.increment_SP()
                STACK = self.dmem[self.get_SP()]
                self.dmem[int(self.current_inst[1][1:])].set_value(STACK)
                self.update_pc_val(self.get_pc_val() + 1)
            else:
                return RETError(self.get_pc_val(), 'No elements left to pop.')
            
        elif inst == 'PUSH':
            sp = self.get_SP()
            if sp < 0x100:
                return StackOverflowError(self.get_pc_val(), f'Cannot push another element to the stack.')

            Rr = self.dmem[int(self.current_inst[1][1:])].value
            self.dmem[sp] = Rr
            self.decrement_SP()
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'RJMP':
            k = int(self.current_inst[1])
            self.update_pc_val(self.get_pc_val() + k + 1)

        elif inst == 'RET':

            # If stack pointer at end or all NOPs afterwards then end
            if (self.get_SP() == DMEM_MAX):
                self.file_end = True
            
            elif (self.get_SP() == DMEM_MAX - 1):
                return RETError(self.get_pc_val(), f'Invalid stack pointer to return from correctly.')

            else:
                self.increment_SP()
                kH = self.dmem[self.get_SP()]   # return location(high) from the stack
                self.increment_SP()
                kL = self.dmem[self.get_SP()]   # return location(low) from the stack
                #if self.pushpop[-1] < 0:        # must have balanced stack pushes & pops to return correctly
                #    return RETError(self.get_pc_val(), f'{-1 * self.pushpop[-1]} too many pops from the stack to return correctly.')
                #elif self.pushpop[-1] > 0:        # must have balanced stack pushes & pops to return correctly
                #    return RETError(self.get_pc_val(), f'{self.pushpop[-1]} too many pushes to the stack to return correctly.')
                    
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

        elif inst == 'SBIW':
            Rdl = self.dmem[int(self.current_inst[1][1:])].value
            Rdh = self.dmem[int(self.current_inst[1][1:]) + 1].value
            K = int(self.current_inst[2])

            R = (256 * Rdh) + Rdl
            R = (R - K) % (256 * 256)
            RLow = R % 256
            RHigh = int((R - RLow)/256)

            self.dmem[int(self.current_inst[1][1:])].set_value(RLow)
            self.dmem[int(self.current_inst[1][1:]) + 1].set_value(RHigh)
            self.update_pc_val(self.get_pc_val() + 1)

            Rdh = self.make_8_bit_binary(Rdh)
            Rdl = self.make_8_bit_binary(Rdl)
            R = self.make_n_bit_binary(R, 16)

            self.sreg.value[5] = int(R[0])
            self.sreg.value[6] = int(R == '0000000000000000')
            self.sreg.value[4] = (1- int(R[0])) & int(Rdh[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[7] = (1- int(R[0])) & int(Rdh[0])

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

        elif inst == 'SBRC':
            Rr = self.dmem[int(self.current_inst[1][1:])].value
            b = int(self.current_inst[2])
            
            R = (Rr & (2**b)) == 0 # check the b-th bit of R

            if R and (self.pmem[self.get_pc_val() + 2] != None): self.update_pc_val(self.get_pc_val() + 2)
            elif R: self.update_pc_val(self.get_pc_val() + 3)
            else: self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'SBRS':
            Rr = self.dmem[int(self.current_inst[1][1:])].value
            b = int(self.current_inst[2])
            
            R = (Rr & (2**b)) != 0 # check the b-th bit of R

            if R and (self.pmem[self.get_pc_val() + 2] != None): self.update_pc_val(self.get_pc_val() + 2)
            elif R: self.update_pc_val(self.get_pc_val() + 3)
            else: self.update_pc_val(self.get_pc_val() + 1)

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
            val = self.get_XYZ(XYZ) # dmem value in XYZ
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            self.dmem[val] = Rr
            self.update_pc_val(self.get_pc_val() + 1)
            self.increment_XYZ(XYZ) # increments XYZ if necessary

        elif inst == 'STD':
            XYZ = self.current_inst[1]
            q = int(self.current_inst[2])
            val = self.get_XYZ(XYZ) + q # dmem value in XYZ
            Rr = self.dmem[int(self.current_inst[3][1:])].value
            self.dmem[val] = Rr
            self.update_pc_val(self.get_pc_val() + 1)

        elif inst == 'STS':
            Rr = self.dmem[int(self.current_inst[2][1:])].value
            self.dmem[int(self.current_inst[1])] = Rr
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

        elif inst == 'TST':
            Rd = self.dmem[int(self.current_inst[1][1:])].value
            R = Rd & Rd

            self.dmem[int(self.current_inst[1][1:])].set_value(R)
            self.update_pc_val(self.get_pc_val() + 1)

            R = self.make_8_bit_binary(R)
            self.sreg.value[4] = 0
            self.sreg.value[5] = int(R[0])
            self.sreg.value[3] = self.sreg.value[4] ^ self.sreg.value[5]
            self.sreg.value[6] = int(R == '00000000')


        elif inst == 'XCH':
            Z = self.get_XYZ('Z')
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
        
        elif inst == 'ADIW':
            d = self.make_n_bit_binary(int((int(instruction[1][1:]) - 24)/2), 2) # reg number converted to binary
            K = self.make_n_bit_binary(instruction[2], 6) # reg number converted to binary
            return f'10010110{K[0:2]}{d}{K[2:]}'

        elif inst == 'AND':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            r = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'001000{r[0]}{d}{r[1:]}'
        
        elif inst == 'ANDI':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            K = self.make_n_bit_binary(instruction[2], 8) # reg number converted to binary
            return f'0111{K[0:4]}{d[1:]}{K[4:]}'

        elif inst == 'ASR':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'1001010{d}0101'

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
            return [f'1001000{d}0000', k]
        
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

        elif inst == 'MOVW':
            d = int(instruction[1][1:])
            r = int(instruction[2][1:])
            d = self.make_n_bit_binary(d, 5) # reg number converted to binary
            r = self.make_n_bit_binary(r, 5) # reg number converted to binary
            return f'00000001{d[:4]}{r[:4]}'
        
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
        
        elif inst == 'RJMP':
            k = self.twos_comp(instruction[1], 12)
            return f'1100{k}'

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

        elif inst == 'SBIW':
            d = self.make_n_bit_binary(int((int(instruction[1][1:]) - 24)/2), 2) # reg number converted to binary
            K = self.make_n_bit_binary(instruction[2], 6) # reg number converted to binary
            return f'10010111{K[0:2]}{d}{K[2:]}'

        elif inst == 'SBR':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            K = self.make_n_bit_binary(instruction[2], 8) # reg number converted to binary
            return f'0110{K[0:4]}{d[1:]}{K[4:]}'

        elif inst == 'SBRC':
            r = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            b = self.make_n_bit_binary(instruction[2], 3)
            return f'1111110{r}0{b}'

        elif inst == 'SBRS':
            r = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            b = self.make_n_bit_binary(instruction[2], 3)
            return f'1111111{r}0{b}'

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
            return [f'1001001{d}0000', k]

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

        elif inst == 'TST':
            d = self.make_n_bit_binary(instruction[1][1:], 5) # reg number converted to binary
            return f'001000{d[0]}{d}{d[1:]}'

        elif inst == 'XCH':
            d = self.make_n_bit_binary(instruction[2][1:], 5) # reg number converted to binary
            return f'1001001{d}0100'


##################################################################################################################
#  SIM
##################################################################################################################

class App:

    def __init__(self, root, data):
        self.root = root
        self.data = data
        self.data_copy = copy.deepcopy(data)
        self.interpreter = Interpreter(self.data[0], self.data[1], self.data[2], self.data[3])
        self.dmem_length = len(self.data[0])
        self.pmem_length = len(self.data[1])
        
        self.root.title('AVR Sim')

        self.reload = 0     # if true when the app closes, the app will reboot (for when updating code)

        ########## Key Binds ##########
        self.root.protocol("WM_DELETE_WINDOW", self.root.quit)              # exit correctly with close window button
        self.root.bind("<Escape>", lambda e: self.root.quit())              # exit with < Esc >
        self.root.bind("<Control-r>", lambda e: self.run())                 # run with < Ctrl+R >
        self.root.bind("<Control-s>", lambda e: self.step())                # step with < Ctrl+S >
        self.root.bind("<Control-e>", lambda e: self.reset())               # reset with < Ctrl+E >
        self.root.bind("<Control-c>", lambda e: self.clear_console())       # clear console with < Ctrl+C >
        self.root.bind("<Control-u>", lambda e: self.refresh())             # nupdate file with < Ctrl+U >
        self.root.bind("<Control-n>", lambda e: self.new())                 # open new file with < Ctrl+U >

        ########## Window Colours ##########
        w = 'white'
        b = 'black'
        o = 'orange'
        g = 'gray12'
        r = 'red'
        bl = 'blue'
        v = 'blue violet'

        self.text_colour = b        # colour of all text in boxes
        self.text_bg = w            # background of text boxes
        self.background = g         # background of the screen
        self.label_colour = b       # colour of the title labels
        self.label_text = w         # colour of the title text
        self.button_text = b        # colour of text on buttons
        self.button_colour = o      # colour of the buttons
        self.change_colour = r      # colour when a value changes from the last operation
        self.last_PC_colour = bl
        self.mix_lastPC_change_colour = v

        self.font = 'Calibri'

        ########## Number Display Type ##########
            # Options = 2's comp (+-), dec, hex, bin
        self.num_disp = 'DEC'
        self.ram_disp = 'DEC'

        ########## Update Tracking ##########
        self.last_sreg = [i for i in self.interpreter.sreg.value]

        self.last_SP = [( self.interpreter.get_SP() % 256 ),
                        int((self.interpreter.get_SP() - self.interpreter.get_SP()%256) / 256),
                        hex(self.interpreter.get_SP())]

        ########## Window sizes ##########
        self.ww = self.root.winfo_screenwidth()      # window width
        self.wh = round(0.92*self.root.winfo_screenheight())     # window height
        #self.ww = 1200
        #self.wh = 750
        self.root.geometry(f'{self.ww}x{self.wh}')
        #self.root.attributes('-fullscreen',True)


        ########## Display ##########
        Frame(master=self.root, width=10*self.ww, height=10*self.wh, bg=self.background).place(x=0,y=0)

        self.displayed_before = False

        self.text_boxes()   # initialise input boxes
        self.buttons()      # initialise buttons
        self.display()      # display the rest

    def display(self):
        label_font_size = round(self.wh/60)
        frame_height = round(self.wh/30)

        sreg = self.interpreter.sreg

        ############ Fixing any text box issues ############
        steps = self.step_box.get('1.0',END)
        for elem in steps:
            if elem not in DIGITS:
                steps = steps.split(elem)[0]
                if len(steps) == 0: steps = '1'
                self.step_box.delete('1.0', END)
                self.step_box.insert(END, steps)
                break

        inst_at = self.inst_y_box.get('1.0',END)
        for elem in inst_at:
            if elem not in DIGITS:
                inst_at = inst_at.split(elem)[0]
                if len(inst_at) == 0: inst_at = '1'
                self.inst_y_box.delete('1.0', END)
                self.inst_y_box.insert(END, inst_at)
                break

        ram_at = self.ram_y_box.get('1.0',END)
        for i, elem in enumerate(ram_at):
            if elem.lower() not in (DIGITS + 'abcdef'):
                if ((i != 1) or (elem not in 'Xx')) and (elem != '\n'):
                    self.ram_y_box.delete('1.0', END)
                    self.ram_y_box.insert(END, '0x100')
                    break
        
        ############ Registers ############
        regx = 0.48 * self.ww
        regy = 0.05 * self.wh
        reg_width = round(self.ww/4.1)
        reg_height = round(self.wh/1.6)

        reg_title = Frame(self.root, bg=self.label_colour,height=frame_height,width=reg_width)
        reg_title.place(x=regx,y=regy-(0.04*self.wh), anchor = 'n')

        reg_label = Label(self.root,text='Registers',font=(self.font,label_font_size),bg=self.label_colour,fg=self.label_text)
        reg_label.place(x=regx,y=regy-(0.04*self.wh), anchor = 'n')
       


        #reg_box = Frame(self.root,height=reg_height,width=reg_width,bg=self.text_bg,borderwidth=5,relief='sunken')
        #reg_box.place(x=regx,y=regy, anchor = 'n')
        #
        #for i in range(32):
        #    reg = self.interpreter.dmem[i]
        #    val = self.convert_val_to_type(reg.value, False)
        #    disp = f'R{i}: ' + ('  ' * int(i < 10)) + f'{val}'
        #    if reg.changed == 1:
        #        reg_label = Label(text=disp,font=(self.font,15),bg=self.text_bg,fg=self.change_colour)
        #    else:
        #        reg_label = Label(text=disp,font=(self.font,15),bg=self.text_bg,fg=self.text_colour)
        #    x = regx + (- 0.11 + ( 0.11 * int(i > 15) )) * self.ww
        #    y = regy + (0.018 + (i * 0.037) - (0.592 * int(i > 15))) * self.wh
        #    reg_label.place(x=x, y=y)
        #    reg.new_instruct()


        font_size = round(self.wh/65) + 2
        reg_box = Text(self.root,height=18,width=29,bg=self.text_bg,fg=self.text_colour,font=(self.font,font_size))
        reg_box.config(borderwidth=5,relief='sunken')
        reg_box.place(x=regx,y=regy, anchor = 'n')


        reg_box.insert(END,'\n')
        for i in range(16):
            val1 = str(self.convert_val_to_type(self.interpreter.dmem[i].value, False, False))
            val2 = str(self.convert_val_to_type(self.interpreter.dmem[i+16].value, False, False))
            
            if self.num_disp == 'BIN':
                val1 = val1[2:]
                val2 = val2[2:]
            
            line_a = f' R{i}:' + (' ' * (1 + 2*(i < 10))) + f'{val1}' + '  ' * (11 - len(val1))
            line_b = f'R{i+16}: {val2}\n'
            reg_box.insert(END, line_a + line_b)

            if self.interpreter.dmem[i].changed == 1:
                reg_box.tag_add(str(i), f'{i+2}.0', f'{i+2}.{len(line_a)}')
                reg_box.tag_configure(str(i), foreground=self.change_colour)
            
            if self.interpreter.dmem[i+16].changed == 1:
                reg_box.tag_add(str(i+16), f'{i+2}.{len(line_a)}', f'{i+2}.{len(line_a + line_b)}')
                reg_box.tag_configure(str(i+16), foreground=self.change_colour)

        reg_box.config(state=DISABLED)
        

        ############ SREG ############
        sregx = 0.48 * self.ww
        sregy = 0.78 * self.wh
        sreg_width = round(self.ww/4)
        sreg_height = round(self.wh/10.2)

        sreg_title = Frame(self.root, bg=self.label_colour,height=frame_height,width=reg_width)
        sreg_title.place(x=sregx,y=sregy-(0.04*self.wh), anchor = 'n')

        sreg_label = Label(self.root,text='Status Register',font=(self.font,label_font_size),bg=self.label_colour,fg=self.label_text)
        sreg_label.place(x=sregx,y=sregy-0.04*self.wh, anchor = 'n')
        
        #sreg_box = Frame(self.root,height=sreg_height,width=sreg_width,bg=self.text_bg,borderwidth=5,relief='sunken')
        #sreg_box.place(x=sregx,y=sregy, anchor = 'n')

        #flags = ['I', 'T', 'H', 'S', 'V', 'N', 'Z', 'C']
        #for i in range(8):
        #    x = sregx + (- 1/8 + 0.026*(i+1)) * self.ww
        #    y = sregy + 0.01 * self.wh
        #    
        #    if sreg.value[i] != self.last_sreg[i]:
        #        sreg_label = Label(text=flags[i],font=(self.font,20),bg=self.text_bg,fg=self.change_colour)
        #        val_label = Label(text=sreg.value[i],font=(self.font,20),bg=self.text_bg,fg=self.change_colour)
        #    
        #    else:
        #        sreg_label = Label(text=flags[i],font=(self.font,20),bg=self.text_bg,fg=self.text_colour)
        #        val_label = Label(text=sreg.value[i],font=(self.font,20),bg=self.text_bg,fg=self.text_colour)
        #    
        #    sreg_label.place(x=x, y=y)
        #    val_label.place(x=x, y=y + 0.035*self.wh)
        
        font_size = round(self.wh/65) + 4
        sreg_box = Text(self.root,font=(self.font,font_size),height=2,width=24,bg=self.text_bg,fg=self.text_colour)
        sreg_box.config(borderwidth=5,relief='sunken')
        sreg_box.place(x=sregx,y=sregy, anchor = 'n')

        flags = ['I', 'T', 'H', 'S', 'V', 'N', 'Z', 'C']

        sreg_box.insert(END, f'   I    T    H    S    V    N    Z    C\n   {sreg.value[0]}')
        for i in range(1,8):
            sreg_box.insert(END, f'    {sreg.value[i]}')
            if sreg.value[i] != self.last_sreg[i]:
                sreg_box.tag_add(flags[i], f'1.{5*i + 3}', f'1.{5*i + 4}')
                sreg_box.tag_configure(flags[i], foreground=self.change_colour)

                sreg_box.tag_add(f'{flags[i]}_val', f'2.{5*i + 3}', f'2.{5*i + 4}')
                sreg_box.tag_configure(f'{flags[i]}_val', foreground=self.change_colour)

        sreg_box.config(state=DISABLED)

        self.last_sreg = [i for i in sreg.value] # update for next iteration

        sreg_label = Label(text='Status Register',font=(self.font,label_font_size),bg=self.label_colour,fg=self.label_text)
        sreg_label.place(x=sregx,y=sregy-(0.04*self.wh), anchor = 'n')
        

        ############ Instructions ############
        instx = 0.255 * self.ww
        insty = 0.05 * self.wh
        inst_width = round(self.ww/6)
        inst_height = round(self.wh/1.4)

        
        p = self.interpreter.get_pc_val() # for putting into the instruction location box where the instruction is at
        if p < 10:
            self.inst_y_box.delete('1.0', END)
            self.inst_y_box.insert(END, '0')
        else:
            self.inst_y_box.delete('1.0', END)
            self.inst_y_box.insert(END, f'{p - 10}')

        inst_title = Frame(self.root, bg=self.label_colour,height=frame_height,width=inst_width)
        inst_title.place(x=instx,y=insty-0.04*self.wh, anchor = 'n')

        inst_label = Label(self.root,text='Instructions',font=(self.font,label_font_size),bg=self.label_colour,fg=self.label_text)
        inst_label.place(x=instx,y=insty-0.04*self.wh, anchor = 'n')

        font_size = round(self.wh/100) + 2
        inst_box = Text(self.root,height=50-font_size,width=26,bg=self.text_bg,fg=self.text_colour)
        inst_box.config(font=(self.font,font_size),borderwidth=5,relief='sunken')
        inst_box.place(x=instx, y=insty, anchor = 'n')

        inst_scrollbar = Scrollbar(self.root, orient='vertical',command=inst_box.yview)
        inst_scrollbar.place(x=instx + 0.082*self.ww,y=insty,height=inst_height, anchor = 'ne')

        for i in range(self.pmem_length): # inserting into box
            inst_ls = self.interpreter.pmem[i]
            if self.num_disp == 'BIN': # binary instructions
                if inst_ls == None: inst = self.interpreter.get_binary_instruction(self.interpreter.pmem[i-1])[1]
                else: inst = self.interpreter.get_binary_instruction(inst_ls)

                if isinstance(inst, list): inst = inst[0]
                inst = f'{i}: {inst}\n'
            
            elif self.num_disp == 'HEX': # hex instructions
                if inst_ls == None: inst = self.interpreter.get_binary_instruction(self.interpreter.pmem[i-1])[1]
                else: inst = self.interpreter.get_binary_instruction(inst_ls)
                if isinstance(inst, list): inst = inst[0]
                inst = hex(int(inst, 2))
                for l in range(len(inst), 6):
                    inst = inst[0:2] + '0' + inst[2:]
                inst = f'{i}: {inst}\n'

            else: # regular instructions
                if inst_ls == None: inst = f'{i}: (double size inst.)\n'
                elif len(inst_ls) == 1: inst = f'{i}: {inst_ls[0]}\n'
                elif len(inst_ls) == 2: inst = f'{i}: {inst_ls[0]} {inst_ls[1]}\n'
                elif len(inst_ls) == 3: inst = f'{i}: {inst_ls[0]} {inst_ls[1]}, {inst_ls[2]}\n'
                elif inst_ls[0] == 'STD': inst = f'{i}: {inst_ls[0]} {inst_ls[1]}{inst_ls[2]}, {inst_ls[3]}\n'
                elif inst_ls[0] == 'LDD': inst = f'{i}: {inst_ls[0]} {inst_ls[1]}, {inst_ls[2]}{inst_ls[3]}\n'

            inst_box.insert(END, inst)
        
        if isinstance(self.interpreter.last_pc, int):
            inst_box.tag_add("Last Line", f'{self.interpreter.last_pc+1}.0', f'{self.interpreter.last_pc+2}.0')
            inst_box.tag_configure("Last Line", foreground=self.last_PC_colour,background=self.text_bg) # colouring the line up to in red

        inst_box.tag_add("Current Line", f'{self.interpreter.get_pc_val()+1}.0', f'{self.interpreter.get_pc_val()+2}.0')
        inst_box.tag_configure("Current Line", foreground=self.change_colour,background=self.text_bg) # colouring the line up to in red
        
        if (self.interpreter.last_pc == self.interpreter.get_pc_val()):   # if PC = last PC
            inst_box.tag_configure("Current Line", foreground=self.mix_lastPC_change_colour,background=self.text_bg) # colouring the line up to in red

        inst_box.config(state=DISABLED)
        #inst_box.yview_moveto(inst_box.yview()[1])

        inst_view = (1 + int(self.inst_y_box.get('1.0',END))) / 0x4001
        if inst_view >= 1: inst_view = 0x3FD6/0x4001 # last section of the inst memory
        inst_box.yview_moveto(inst_view)


        ############ RAM ############
        ramx = 0.705 * self.ww
        ramy = 0.05 * self.wh

        #if self.displayed_before:
        #    old_val = round(self.ram_box.yview()[0], 5)

        ram_title = Frame(self.root, bg=self.label_colour,height=frame_height,width=inst_width)
        ram_title.place(x=ramx,y=ramy-0.04*self.wh, anchor = 'n')

        ram_label = Label(self.root,text='RAM',font=(self.font,label_font_size),bg=self.label_colour,fg=self.label_text)
        ram_label.place(x=ramx,y=ramy-0.04*self.wh, anchor = 'n')

        font_size = round(self.wh/100) + 2
        self.ram_box = Text(self.root,height=50-font_size,width=26,bg=self.text_bg,fg=self.text_colour)
        self.ram_box.config(font=(self.font,font_size),borderwidth=5,relief='sunken')
        self.ram_box.place(x=ramx, y=ramy, anchor = 'n')

        for i in range(0x100, self.dmem_length): # inserting into box
            val = self.convert_val_to_type(self.interpreter.dmem[i], True, False)
            val = f'{hex(i)}: {val}\n'
            self.ram_box.insert(END, val)

        self.ram_scrollbar = Scrollbar(self.root, orient='vertical',command=self.ram_box.yview)
        self.ram_scrollbar.place(x=ramx + 0.082*self.ww,y=ramy,height=inst_height, anchor = 'ne')
        
        #if self.displayed_before:
        #    self.ram_scrollbar.set(old_val, old_val)

        self.ram_box.config(state=DISABLED)
        #self.ram_box.yview_moveto(self.ram_box.yview()[1])


        # Converting to values 
        ram_view_val = self.ram_y_box.get('1.0',END)
        if ram_view_val.lower()[1] == 'x':
            if len(ram_view_val) < 5: ram_view = 0x100
            else: ram_view = int(self.ram_y_box.get('1.0',END), 16)
        else: ram_view = int(self.ram_y_box.get('1.0',END))
        
        if ram_view < 0x100: ram_view = 0x100
        elif ram_view > DMEM_MAX: ram_view = DMEM_MAX - 42
        
        ram_view = (ram_view - 0xFF)/(DMEM_MAX - 0xFF)
        self.ram_box.yview_moveto(ram_view)

        #if self.displayed_before:
        #    self.ram_box.yview_moveto(old_val)


        #### Other
        otherx = 0.89 * self.ww
        othery = 0.05 * self.wh
        other_width = round(self.ww/6)
        font_size = round(self.wh/50) + 2

            #PC Box

        #PC_box = Frame(self.root,height=round(self.wh/10),width=other_width,bg=self.text_bg,borderwidth=5,relief='sunken')
        #PC_box.place(relx=otherx, rely=othery, anchor = 'n')

        #PC_title = Frame(self.root, bg=self.label_colour,height=frame_height,width=other_width)
        #PC_title.place(relx=otherx,rely=othery-0.038, anchor = 'n')

        #PC_label = Label(self.root,text='Other',font=(self.font,15),bg=self.label_colour,fg=self.label_text)
        #PC_label.place(relx=otherx,rely=othery-0.038, anchor = 'n')

        #PC_val_label = Label(self.root,text=f'PC: {self.interpreter.get_pc_val()}',font=(self.font,30),bg=self.text_bg,fg=self.text_colour)
        #PC_val_label.place(relx=otherx-0.07,rely=othery+0.02, anchor = 'nw')

        Other_title = Frame(self.root, bg=self.label_colour,height=frame_height,width=other_width)
        Other_title.place(x=otherx,y=othery-0.04*self.wh, anchor = 'n')

        Other_label = Label(self.root,text='Other',font=(self.font,label_font_size),bg=self.label_colour,fg=self.label_text)
        Other_label.place(x=otherx,y=othery-0.04*self.wh, anchor = 'n')

        PC_box = Text(self.root,height=2,width=15,bg=self.text_bg,fg=self.text_colour)
        PC_box.config(borderwidth=5,relief='sunken',font=(self.font,font_size))
        PC_box.place(x=otherx, y=othery, anchor = 'n')

        PC_box.insert(END, f'  Prev. PC: {self.interpreter.last_pc}')
        PC_box.insert(END, f'\n  PC: {self.interpreter.get_pc_val()}')
        PC_box.config(state=DISABLED)


            # XYZ Box

        #XYZ_box = Frame(self.root,height=round(self.wh/7),width=other_width,bg=self.text_bg,borderwidth=5,relief='sunken')
        #XYZ_box.place(relx=otherx, rely=othery+0.11, anchor = 'n')

        #xyz = ['X', 'Y', 'Z']
        #for i in range(3):
            #val = self.convert_val_to_type(self.interpreter.get_XYZ(xyz[i]), False)
            #XYZ_val = f'{xyz[i]}: {val}'
            #XYZ_val_label = Label(self.root,text=XYZ_val,font=(self.font,14),bg=self.text_bg,fg=self.text_colour)
            #XYZ_val_label.place(relx=otherx-0.075,rely=othery+0.125 + (0.0405 * i), anchor = 'nw')

        XYZ_box = Text(self.root,height=3,width=15,bg=self.text_bg,fg=self.text_colour)
        XYZ_box.config(borderwidth=5,relief='sunken',font=(self.font,font_size))
        XYZ_box.place(x=otherx, y=othery+0.12*self.wh, anchor = 'n')

        for i, elem in enumerate(['X', 'Y', 'Z']):
            val = self.convert_val_to_type(self.interpreter.get_XYZ(elem), False, True)
            XYZ_box.insert(END, f'  {elem}: {val}')
            if elem != 'Z': XYZ_box.insert(END, '\n')
            if self.interpreter.dmem[26 + 2*i].changed or self.interpreter.dmem[27 + 2*i].changed: # dealing with change colouring
                XYZ_box.tag_add(elem, f'{i+1}.0', f'{i+2}.0')
                XYZ_box.tag_configure(elem, foreground=self.change_colour,background=self.text_bg)

        XYZ_box.config(state=DISABLED)

            # SP BOX
        #SP_box = Frame(self.root,height=round(self.wh/7),width=other_width,bg=self.text_bg,borderwidth=5,relief='sunken')
        #SP_box.place(relx=otherx, rely=othery+0.26, anchor = 'n')

        #SPL_val = f'SPL: {self.interpreter.get_SP()%256}'
        #SPL_val_label = Label(self.root,text=SPL_val,font=(self.font,15),bg=self.text_bg,fg=self.text_colour)
        #SPL_val_label.place(relx=otherx-0.07,rely=othery+0.28, anchor = 'nw')

        #SPH_val = f'SPH: {int((self.interpreter.get_SP() - self.interpreter.get_SP()%256) / 256)}'
        #SPH_val_label = Label(self.root,text=SPH_val,font=(self.font,15),bg=self.text_bg,fg=self.text_colour)
        #SPH_val_label.place(relx=otherx-0.07,rely=othery+0.32, anchor = 'nw')

        #SP_val = f'SP: {hex(self.interpreter.get_SP())}'
        #SP_val_label = Label(self.root,text=SP_val,font=(self.font,15),bg=self.text_bg,fg=self.text_colour)
        #SP_val_label.place(relx=otherx-0.07,rely=othery+0.36, anchor = 'nw')
        
        SP_box = Text(self.root,height=3,width=15,bg=self.text_bg,fg=self.text_colour)
        SP_box.config(borderwidth=5,relief='sunken',font=(self.font,font_size))
        SP_box.place(x=otherx, y=othery+0.28*self.wh, anchor = 'n')

        val = self.interpreter.get_SP() % 256
        SP_box.insert(END, f'  SPL: {val}\n')
        if val != self.last_SP[0]:
            SP_box.tag_add('SPL', '1.0', '2.0')
            SP_box.tag_configure('SPL', foreground=self.change_colour,background=self.text_bg)
        
        val = int((self.interpreter.get_SP() - self.interpreter.get_SP()%256) / 256)
        SP_box.insert(END, f'  SPH: {val}\n')
        if val != self.last_SP[1]:
            SP_box.tag_add('SPH', '2.0', '3.0')
            SP_box.tag_configure('SPH', foreground=self.change_colour,background=self.text_bg)

        val = hex(self.interpreter.get_SP())
        SP_box.insert(END, f'  SP: {val}')
        if val != self.last_SP[2]:
            SP_box.tag_add('SP', '3.0', '4.0')
            SP_box.tag_configure('SP', foreground=self.change_colour,background=self.text_bg)

        SP_box.config(state=DISABLED)

        self.displayed_before = True

    def text_boxes(self):
        """
        For the boxes on the side of the screen
        to be inputted to.
        """

        x_val = 0.085 * self.ww
        label_font_size = round(self.wh/60)
        frame_height = round(self.wh/30)

        ########## Step Size ##########
        self.step_box = Text(self.root,height=1,width=10,bg=self.text_bg,fg=self.text_colour,borderwidth=4,relief='sunken',font=(self.font,20))
        self.step_box.place(x=x_val,y=0.387*self.wh, anchor = 'n')
        self.step_box.insert(END, '1') # initial step size

        ########## Inst Y View ##########
        inst_y_title = Frame(self.root, bg=self.label_colour,height=frame_height,width=150)
        inst_y_title.place(x=x_val,y=0.455*self.wh, anchor = 'n')

        inst_y_label = Label(self.root,text='Instructions at:',font=(self.font,label_font_size),bg=self.label_colour,fg=self.label_text)
        inst_y_label.place(x=x_val,y=0.455*self.wh, anchor = 'n')

        self.inst_y_box = Text(self.root,height=1,width=10,bg=self.text_bg,fg=self.text_colour,borderwidth=4,relief='sunken',font=(self.font,20))
        self.inst_y_box.place(x=x_val,y=0.5*self.wh, anchor = 'n')
        self.inst_y_box.insert(END, '0') # initial location

        ########## RAM Y View ##########
        ram_y_title = Frame(self.root, bg=self.label_colour,height=frame_height,width=150)
        ram_y_title.place(x=x_val,y=0.56*self.wh, anchor = 'n')
        
        ram_y_label = Label(self.root,text='RAM at:',font=(self.font,label_font_size),bg=self.label_colour,fg=self.label_text)
        ram_y_label.place(x=x_val,y=0.56*self.wh, anchor = 'n')
        
        self.ram_y_box = Text(self.root,height=1,width=10,bg=self.text_bg,fg=self.text_colour,borderwidth=4,relief='sunken',font=(self.font,20))
        self.ram_y_box.place(x=x_val,y=0.6*self.wh, anchor = 'n')
        self.ram_y_box.insert(END, '0x100') # initial location

        ########## Console Box ##########
        otherx = 0.89 * self.ww
        othery = 0.05 * self.wh
        font_size = round(self.wh/80)

        console_box_title = Frame(self.root, bg=self.label_colour,height=frame_height,width=round(self.ww/6))
        console_box_title.place(x=otherx,y=othery+0.44*self.wh, anchor = 'n')

        console_box_label = Label(self.root,text='Console',font=(self.font,label_font_size),bg=self.label_colour,fg=self.label_text)
        console_box_label.place(x=otherx,y=othery+0.44*self.wh, anchor = 'n')

        self.console_box = Text(self.root,font=(self.font,font_size),height=16,width=27,bg=self.text_bg,fg=self.text_colour)
        self.console_box.config(borderwidth=5,relief='sunken')
        self.console_box.place(x=otherx, y=othery+0.48*self.wh, anchor = 'n')

    def buttons(self):
        
        x_val = 0.085 * self.ww
        x_val2 = 0.25 * self.ww

        #### Run Buttons ####
        reset_button = Button(self.root,text='Reset',font=(self.font,15))
        reset_button.config(bg=self.button_colour,fg=self.button_text,height=2,width=14)
        reset_button.config(command=self.reset)
        reset_button.place(x=x_val,y=0.05*self.wh, anchor = 'n')
        
        run_file_button = Button(self.root,text='Run File',font=(self.font,15))
        run_file_button.config(bg=self.button_colour,fg=self.button_text,height=2,width=14)
        run_file_button.config(command=self.run)
        run_file_button.place(x=x_val,y=0.17*self.wh, anchor = 'n')

        step_button = Button(self.root,text='Step',font=(self.font,15))
        step_button.config(bg=self.button_colour,fg=self.button_text,height=2,width=14)
        step_button.config(command=self.step)
        step_button.place(x=x_val,y=0.29*self.wh, anchor = 'n')

        #quit_button = Button(self.root,text='Quit',font=(self.font,17))
        #quit_button.config(bg=self.button_colour,fg=self.button_text,height=2,width=12)
        #quit_button.config(command=self.root.quit)
        #quit_button.place(x=x_val,y=0.87*self.wh, anchor = 'n')


        #### Display Buttons ####
        font_size = round(self.wh/60)

        disp_title = Frame(self.root, bg=self.label_colour,height=round(self.wh/30),width=150)
        disp_title.place(x=x_val,y=0.66*self.wh, anchor = 'n')

        disp_label = Label(self.root,text='Display Type',font=(self.font,font_size),bg=self.label_colour,fg=self.label_text)
        disp_label.place(x=x_val,y=0.66*self.wh, anchor = 'n')

        tcomp_button = Button(self.root,text='2\'s Comp',font=(self.font,font_size))
        tcomp_button.config(bg=self.button_colour,fg=self.button_text,height=1,width=8)
        tcomp_button.config(command=self.update_to_tcomp_type)
        tcomp_button.place(x=0.063*self.ww,y=0.71*self.wh, anchor = 'n')

        dec_button = Button(self.root,text='Dec',font=(self.font,font_size))
        dec_button.config(bg=self.button_colour,fg=self.button_text,height=1,width=4)
        dec_button.config(command=self.update_to_dec_type)
        dec_button.place(x=0.121*self.ww,y=0.71*self.wh, anchor = 'n')

        hex_button = Button(self.root,text='Hex',font=(self.font,font_size))
        hex_button.config(bg=self.button_colour,fg=self.button_text,height=1,width=3)
        hex_button.config(command=self.update_to_hex_type)
        hex_button.place(x=0.045*self.ww,y=0.77*self.wh, anchor = 'n')

        bin_button = Button(self.root,text='Bin',font=(self.font,font_size))
        bin_button.config(bg=self.button_colour,fg=self.button_text,height=1,width=3)
        bin_button.config(command=self.update_to_bin_type)
        bin_button.place(x=0.081*self.ww,y=0.77*self.wh, anchor = 'n')

        text_button = Button(self.root,text='Text',font=(self.font,font_size))
        text_button.config(bg=self.button_colour,fg=self.button_text,height=1,width=4)
        text_button.config(command=self.update_to_text_type)
        text_button.place(x=0.121*self.ww,y=0.77*self.wh, anchor = 'n')

        #### Clear Console Button ####
        clear_console_button = Button(self.root,text='Clear Console',font=(self.font,font_size))
        clear_console_button.config(bg=self.button_colour,fg=self.button_text,height=1,width=14)
        clear_console_button.config(command=self.clear_console)
        clear_console_button.place(x=x_val,y=0.84*self.wh, anchor = 'n')

        #### Refresh Button ####
        clear_console_button = Button(self.root,text='Refresh',font=(self.font,font_size))
        clear_console_button.config(bg=self.button_colour,fg=self.button_text,height=1,width=14)
        clear_console_button.config(command=self.refresh)
        clear_console_button.place(x=x_val,y=0.895*self.wh, anchor = 'n')

        #### New File Button ####
        clear_console_button = Button(self.root,text='Load\nNew File',font=(self.font,font_size))
        clear_console_button.config(bg=self.button_colour,fg=self.button_text,height=3,width=14)
        clear_console_button.config(command=self.new)
        clear_console_button.place(x=x_val2,y=0.84*self.wh, anchor = 'n')

    def run(self):
        """
        Runs the whole code
        """
        for i in range(32): # refresh the 'changed' variable
            self.interpreter.dmem[i].new_instruct()

        self.update_last_SP()

        while self.interpreter.file_end == False:
            output = self.interpreter.step()
            if isinstance(output, str):
                self.console_box.insert(END, output)
                self.console_box.yview_moveto(1)

            elif output:  # error
                self.console_box.insert(END, output)
                self.console_box.yview_moveto(1)
                break

        self.display()

    def step(self):
        for i in range(32): # refresh the 'changed' variable
            self.interpreter.dmem[i].new_instruct()

        self.update_last_SP()

        step_size = self.step_box.get('1.0',END)
        try: step_size = int(step_size)
        except: step_size = 1
        for repeat in range(step_size):
            output = self.interpreter.step()
            if isinstance(output, str):
                self.console_box.insert(END, output)
                self.console_box.yview_moveto(1)
            elif output:  # error
                self.console_box.insert(END, output)
                self.console_box.yview_moveto(1)
                break
            
        self.display()

    def reset(self):
        """
        Resets the to be beginning so
        the file can be run again.
        """

        for i in range(32): # refresh the 'changed' variable
            self.interpreter.dmem[i].new_instruct()

        self.last_SP = [0, 0, '0x0'] # resetting expected SP variables

        self.data = copy.deepcopy(self.data_copy)
        self.interpreter = Interpreter(self.data[0], self.data[1], self.data[2], self.data[3])

        self.display()

    def refresh(self):
        self.reload = 1
        self.root.quit()
    
    def new(self):
        self.reload = 2
        self.root.quit()

    def update_to_text_type(self):
        self.update_disp_type('TEXT')

    def update_to_dec_type(self):
        self.update_disp_type('DEC')

    def update_to_hex_type(self):
        self.update_disp_type('HEX')

    def update_to_bin_type(self):
        self.update_disp_type('BIN')

    def update_to_tcomp_type(self):
        self.update_disp_type('TCOMP')

    def update_disp_type(self, type_):
        if type_ == 'TEXT': self.ram_disp = 'TEXT'
        else:
            self.num_disp = type_
            self.ram_disp = type_
        
        self.display()

    def update_last_SP(self):
        self.last_SP[0] = self.interpreter.get_SP() % 256
        self.last_SP[1] = int((self.interpreter.get_SP() - self.interpreter.get_SP()%256) / 256)
        self.last_SP[2] = hex(self.interpreter.get_SP())

    def clear_console(self):
        self.console_box.delete('1.0', END)

    def convert_val_to_type(self, val, is_ram: bool, is_XYZ: bool):
        """
        Takes a number and converts
        it to the display type that
        is currently in use.
        """

        if (is_ram):
            if (self.ram_disp == 'TEXT'):
                if val == 0:
                    return 'NULL'
                if (val > 31) and (val < 127):
                    return chr(val)
                if val == 10:
                    return '\\n'
                if (val < 32) or (val > 126):
                    return 'N/A'
            if (self.num_disp == 'TCOMP'):
                if val < 128: return val
                return val - 256
                

        if self.num_disp == 'DEC':
            return str(val)

        if self.num_disp == 'BIN':
            if is_XYZ: n = 16
            else: n = 8
            b = bin(val)[2:]
            while len(b) < n:
                b = '0' + b
            return '0b' + b

        if self.num_disp == 'HEX':
            if 0 <= val <= 255: n = 2
            if val > 255: n = 4
            else: n = 2
            h = hex(val)[2:]
            while len(h) < n:
                h = '0' + h
            return '0x' + h

        if self.num_disp == 'TCOMP':
            if (val > 0x7F) and (val < 0x100): return val - 0x100
            elif (val > 0x7FFF): return val - 0x10000
            return val


##################################################################################################################
#  AN EASTER EGG - POEM
##################################################################################################################

"""
O that you would know my heart,
Your ways, greater than my own,
To you I give my every hour,
Just to you and you alone.

O that you would see my eyes,
Looking only at your shape,
Spending time in your presence,
Looking at you for escape.

O that you would know my mind,
Long I strive to let you see,
Night and day I work for you,
Just for you, not you for me.

O that you would see my hands,
Patiently they labour strong,
Intro to Computer Systems,
Man, you're tough and very long.
"""


##################################################################################################################
#  RUN
##################################################################################################################

def run(fn, text):

    ########### Lexer ###########
    lexer = Lexer(fn, text)
    tokens, error = lexer.make_tokens()
    if error or (len(tokens) == 0):
        return tokens, error.as_string()

    line_nums = tokens[-1]                  # allocating the locations of each line
    tokens = tokens[0:(len(tokens) - 1)]    # removing line nums from last pos in tokens

    ########### Parser ###########
    parser = Parser(fn, tokens, line_nums)
    result, error = parser.parse()
    if error:
        return result, error.as_string()

    instructions = result[0]
    inst_length = len(instructions)
    for i in range(len(PMEM)): # PMEM & DMEM imported from avr_reg.py
        if i < len(instructions): PMEM[i] = instructions[i]
        else: PMEM[i] = ['NOP']

    data = result[1]
    for i in range(len(data)):
        DMEM[i + 0x100] = data[i]


    ########### Simulator ###########
    data = [DMEM, PMEM, fn, inst_length]
    root = Tk()
    app = App(root, data)
    root.mainloop()

    if app.reload != 0:
        root.destroy()
    
    return app.reload, error



if __name__ == '__main__':

    output = 2      # run a new file
    first_run = True

    while True:

        ######################################
        #  DEFINE MEMORY
        ######################################

        pmem_size = 0x4000 # max 0x3FFF
        PMEM = [0x00 for i in range(pmem_size)]

        dem_size = 0x900 # max 0x8FF
        DMEM_MAX = dem_size - 1
        DMEM = [0x00 for i in range(dem_size)]


        ######################################
        #  DEFINE REGISTER FILE
        ######################################

        for i in range(256):
            DMEM[i] = Register('R' + str(i))

        SREG = Register('SREG')
        SREG.value = [0, 0, 0, 0, 0, 0, 0, 0]

        #PCL = Register('PCL')
        #PCH = Register('PCH')


        SPL = Register('SPL')
        low = DMEM_MAX % 256
        SPL.set_value(low)
        #SPL.set_value(L)
        SPH = Register('SPH')
        high = int((DMEM_MAX - low) / 256)
        SPH.set_value(high)
        #SPH.set_value(H)

        #DMEM[0x5B] = PCL # program counter low byte
        #DMEM[0x5C] = PCH # program counter high byte
        DMEM[0x5D] = SPL # stack pointer low byte (0x3D in I/O file)
        DMEM[0x5E] = SPH # stack pointer high byte (0x3E in I/O file)
        DMEM[0x5F] = SREG # status register (0x3F in I/O file)

        REGISTER_FILE = []
        for i in range(32):
            REGISTER_FILE.append(f'R{str(i)}')

        ######################################
        #  GET FILE
        ######################################

        if (output == 2) and first_run:
            if len(sys.argv) < 2:
                Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
                fn = askopenfilename() # show an "Open" dialog box and return the path to the selected file
            
            else: fn = sys.argv[1]

        elif (output == 2):
            Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
            fn = askopenfilename() # show an "Open" dialog box and return the path to the selected file
        
        elif output == 0: break

        ######################################
        #  RUN FILE
        ######################################

        first_run = False

        if fn:
            with open(fn, 'r') as f:
                lines = f.read()
                output, error = run(fn, lines)
                if error:
                    print(error)
                    break
        
        else:
            break
