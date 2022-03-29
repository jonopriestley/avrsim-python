import sys

path = sys.path
sim_path = path[0] + '\\sim'
path.insert(1, sim_path)

from avr_sim import *


"""
To add a new instruction:
- Add to INST_LIST (in lexer.py)
- Add to INST_REQUIREMENTS (in parser_.py)
- Add its execution info Interpreter.step() method (in interpreter.py)
"""

"""
To add a new directive:
- Add to DIRECTIVES list
- Add to Parser.data_label_parse() and Parser.parse() methods
"""

##### ord('a') returns ascii number for 'a' (0x61)
##### chr(0x61) returns 0x61 element in ascii table ('a')



######################################
#  RUN
######################################

def run(fn, text):

    lexer = Lexer(fn, text)
    tokens, error = lexer.make_tokens()
    if error:
        return tokens, error.as_string()

    
    line_nums = tokens[-1]
    tokens = tokens[0:(len(tokens) - 1)] # removing line nums from last pos in tokens

    parser = Parser(fn, tokens, line_nums)
    result, error = parser.parse()
    if error:
        return result, error.as_string()

    instructions = result[0]
    len_inst = len(instructions)
    for i in range(len(PMEM)):
        if i < len(instructions): PMEM[i] = instructions[i]
        else: PMEM[i] = ['NOP']


    data = result[1]
    for i in range(len(data)):
        DMEM[i + 0x100] = data[i]


    do_app = True # make false to run in terminal
    if do_app:
        data = [DMEM, PMEM, fn, len_inst]
        root = Tk()
        app = App(root, data)
        root.mainloop()

        return result, error


    ######## For running in the terminal only

    interpreter = Interpreter(DMEM, PMEM, fn, len_inst)
    while True:
        
        i = input('\nINPUT: ')
        if i.lower() == 'q':
            break
        elif i.lower() == 'r':
            while interpreter.file_end == False:
                interpreter.step()

        elif (len(i) > 0) and i[0] in '0123456789':
            n = int(i)
            for i in range(n):
                interpreter.step()
                if interpreter.file_end:
                    break
        else:
            interpreter.step()
            print('')
            print(interpreter.current_inst)

        print('')
        for r in range(0x20):
            print(interpreter.dmem[r], end = '   ')
            if r % 3 == 2:
                print('')

        sreg_val = ''
        for elem in interpreter.sreg.value:
            sreg_val += str(elem) + ' '
        print(f'\n\nSREG: {sreg_val}')
        print("      I T H S V N Z C")

        if interpreter.file_end:
            break

    return result, error

