import string
from avr_error import *
from avr_pos import *
from avr_reg import *
from avr_tok import *


######################################
#  LEXER
######################################

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
                tok = self.make_InstRegLabelStrDir(directive)
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

    def make_InstRegLabelStrDir(self, directive=None):
        """
        Makes instruction token or
        register token or label token.
        """
        pos_start = self.pos.copy()
        id_str = ''

        while (self.current_char != None) and (self.current_char != '\n') and (self.current_char in (LETTERS + DIGITS + '._()')):
            id_str += self.current_char
            self.advance()

        if self.current_char == ':':
            self.advance()
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
    'SBR',
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
    '.space'
]

