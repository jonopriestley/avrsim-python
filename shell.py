import sys

path = sys.path
sim_path = path[0] + '\\lib'
path.insert(1, sim_path)

from avr_sim import * # import from avr_sim file in sim

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

######################################
#  RUN
######################################

def run(fn, text):

    ########### Tokenizer ###########
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
    for i in range(len(PMEM)):
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
        raise ValueError('Must provide a file name to execute.')

    fn = sys.argv[1]
    with open(fn, 'r') as f:
        lines = f.read()
        output, error = run(fn, lines)
        if error: print(error)
