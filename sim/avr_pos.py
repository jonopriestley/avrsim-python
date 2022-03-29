######################################
#  POSITION
######################################

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
