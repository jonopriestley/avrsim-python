import sys

path = sys.path
sim_path = path[0] + '/lib'
path.insert(1, sim_path)

from avr_sim import * # import from avr_sim file in sim

from tkinter.filedialog import askopenfilename

"""
To add a new instruction:
- Add to INST_LIST (in avr_lexer.py)
- Add to INST_REQUIREMENTS (in avr_parser_.py)
- Add its execution info interpreter.step() method (in avr_interpreter.py)
- Add it's binary info to interpreter get_binary_instruction method
- UDL on Notepadd++ ALREADY has all the instructions

To add a new directive:
- Add to DIRECTIVES list
- Add to Parser.data_label_parse() and Parser.parse() methods
"""

######################################
#  RUN
######################################

def run(fn, text):

    ########### Lexer ###########
    lexer = Lexer(fn, text)
    tokens, error = lexer.make_tokens()
    if error:
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

    return result, error


if __name__ == '__main__':

    
    if len(sys.argv) < 2:
        Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
        fn = askopenfilename() # show an "Open" dialog box and return the path to the selected file
      
    else: fn = sys.argv[1]

    if fn:
        with open(fn, 'r') as f:
            lines = f.read()
            output, error = run(fn, lines)
            if error: print(error)

