import copy
from tkinter import *

from avr_error import *
from avr_interpreter import *
from avr_lexer import *
from avr_parser import *
from avr_pos import *
from avr_reg import *
from avr_tok import *


######################################
#  APP
######################################

class App:

    def __init__(self, root, data):
        self.root = root
        self.data = data
        self.data_copy = copy.deepcopy(data)
        self.interpreter = Interpreter(self.data[0], self.data[1], self.data[2], self.data[3])
        self.dmem_length = len(self.data[0])
        self.pmem_length = len(self.data[1])
        
        self.root.title('AVR Basic Sim')

        ########## Key Binds ##########
        self.root.bind("<Escape>", lambda e: self.root.quit())              # exit with < Esc >
        self.root.bind("<Control-r>", lambda e: self.run())                 # run with < Ctrl+R >
        self.root.bind("<Control-s>", lambda e: self.step())                # step with < Ctrl+S >
        self.root.bind("<Control-e>", lambda e: self.reset())               # reset with < Ctrl+E >
        self.root.bind("<Control-c>", lambda e: self.clear_console())       # clear console with < Ctrl+C >

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

        self.last_XYZ = [str(self.interpreter.get_XYZ('X')),
                        str(self.interpreter.get_XYZ('Y')),
                        str(self.interpreter.get_XYZ('Z'))]

        self.last_SP = [( self.interpreter.get_SP() % 256 ),
                        int((self.interpreter.get_SP() - self.interpreter.get_SP()%256) / 256),
                        hex(self.interpreter.get_SP())]

        ########## Window sizes ##########
        self.ww = self.root.winfo_screenwidth()      # window width
        self.wh = self.root.winfo_screenheight()     # window height
        self.root.geometry(f'{self.ww}x{self.wh}')
        #self.root.attributes('-fullscreen',True)


        ########## Display ##########
        Frame(master=self.root, width=10*self.ww, height=10*self.wh, bg=self.background).place(x=0,y=0)

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
            if elem not in DIGITS:
                if not (i == 1 and elem in 'Xx'):
                    ram_at = ram_at[0:i]
                    if len(ram_at) < 2:
                        ram_at == '0x100'
                    self.ram_y_box.delete('1.0', END)
                    self.ram_y_box.insert(END, ram_at)
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
            val1 = str(self.convert_val_to_type(self.interpreter.dmem[i].value, False))
            val2 = str(self.convert_val_to_type(self.interpreter.dmem[i+16].value, False))
            
            if self.num_disp == 'BIN':
                val1 = val1[2:]
                val2 = val2[2:]
            
            line_a = f' R{i}:' + (' ' * (1 + 2*(i < 10))) + f'{val1}' + '  ' * (11 - len(val1))
            line_b = f'R{i+16}: {val2}\n'
            reg_box.insert(END, line_a + line_b)

            if self.interpreter.dmem[i].changed == 1:
                reg_box.tag_add(str(i), f'{i+2}.0', f'{i+2}.{len(line_a)}')
                reg_box.tag_configure(str(i), foreground=self.change_colour)
            
            self.interpreter.dmem[i].new_instruct()

            if self.interpreter.dmem[i+16].changed == 1:
                reg_box.tag_add(str(i+16), f'{i+2}.{len(line_a)}', f'{i+2}.{len(line_a + line_b)}')
                reg_box.tag_configure(str(i+16), foreground=self.change_colour)
            
            self.interpreter.dmem[i+16].new_instruct()

        reg_box.config(state=DISABLED)
        

        ############ SREG ############
        sregx = 0.48 * self.ww
        sregy = 0.73 * self.wh
        sreg_width = round(self.ww/4)
        sreg_height = round(self.wh/10.2)

        sreg_title = Frame(self.root, bg=self.label_colour,height=frame_height,width=reg_width)
        sreg_title.place(x=sregx,y=sregy-(0.04*self.wh), anchor = 'n')

        sreg_label = Label(text='Status Register',font=(self.font,label_font_size),bg=self.label_colour,fg=self.label_text)
        sreg_label.place(x=sregx,y=sregy-(0.04*self.wh), anchor = 'n')
        
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
        
        font_size = round(self.wh/80) + 6
        sreg_box = Text(self.root,font=(self.font,font_size),height=2,width=24,bg=self.text_bg,fg=self.text_colour)
        sreg_box.config(borderwidth=5,relief='sunken')
        sreg_box.place(x=sregx,y=sregy, anchor = 'n')

        flags = ['I', 'T', 'H', 'S', 'V', 'N', 'Z', 'C']

        sreg_box.insert(END, f'     I    T    H    S    V    N    Z    C\n')
        for i in range(8):
            sreg_box.insert(END, f'    {sreg.value[i]}')

            if sreg.value[i] != self.last_sreg[i]:
                sreg_box.tag_add(flags[i], f'1.{5*i + 5}', f'1.{5*i + 6}')
                sreg_box.tag_configure(flags[i], foreground=self.change_colour)

                sreg_box.tag_add(f'{flags[i]}_val', f'2.{5*i + 4}', f'2.{5*i + 5}')
                sreg_box.tag_configure(f'{flags[i]}_val', foreground=self.change_colour)

        sreg_box.config(state=DISABLED)

        self.last_sreg = [i for i in sreg.value] # update for next iteration



        ############ Instructions ############
        instx = 0.255 * self.ww
        insty = 0.05 * self.wh
        inst_width = round(self.ww/6)
        inst_height = round(self.wh/1.3)

        
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

        font_size = round(self.wh/80)
        inst_box = Text(self.root,height=40,width=26,bg=self.text_bg,fg=self.text_colour)
        inst_box.config(font=(self.font,font_size),borderwidth=5,relief='sunken')
        inst_box.place(x=instx, y=insty, anchor = 'n')

        inst_scrollbar = Scrollbar(self.root, orient='vertical',command=inst_box.yview)
        inst_scrollbar.place(x=instx + 0.082*self.ww,y=insty,height=inst_height-2, anchor = 'ne')

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

        ram_title = Frame(self.root, bg=self.label_colour,height=frame_height,width=inst_width)
        ram_title.place(x=ramx,y=ramy-0.04*self.wh, anchor = 'n')

        ram_label = Label(self.root,text='RAM',font=(self.font,label_font_size),bg=self.label_colour,fg=self.label_text)
        ram_label.place(x=ramx,y=ramy-0.04*self.wh, anchor = 'n')

        font_size = round(self.wh/80)
        ram_box = Text(self.root,height=40,width=26,bg=self.text_bg,fg=self.text_colour)
        ram_box.config(font=(self.font,font_size),borderwidth=5,relief='sunken')
        ram_box.place(x=ramx, y=ramy, anchor = 'n')

        for i in range(0x100, self.dmem_length): # inserting into box
            val = self.convert_val_to_type(self.interpreter.dmem[i], True)
            val = f'{hex(i)}: {val}\n'
            ram_box.insert(END, val)

        ram_scrollbar = Scrollbar(self.root, orient='vertical',command=ram_box.yview)
        ram_scrollbar.place(x=ramx + 0.082*self.ww,y=ramy,height=inst_height-2, anchor = 'ne')

        ram_box.config(state=DISABLED)
        #ram_box.yview_moveto(ram_box.yview()[1])

        ram_view_val = self.ram_y_box.get('1.0',END)

        # Converting to values 
        if 'x' in ram_view_val.lower(): ram_view = int(self.ram_y_box.get('1.0',END), 16)
        else: ram_view = int(self.ram_y_box.get('1.0',END))

        if ram_view < 0x100: ram_view = 0x100
        elif ram_view > 0x8FF: ram_view = 0x8D5

        ram_view = (ram_view - 0xFF)/0x801
        ram_box.yview_moveto(ram_view)

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
            val = self.convert_val_to_type(self.interpreter.get_XYZ(elem), False)
            XYZ_box.insert(END, f'  {elem}: {val}\n')
            if val != self.last_XYZ[i]: # dealing with change colouring
                XYZ_box.tag_add(elem, f'{i+1}.0', f'{i+2}.0')
                XYZ_box.tag_configure(elem, foreground=self.change_colour,background=self.text_bg)

        XYZ_box.config(state=DISABLED)

        self.last_XYZ = [str(self.interpreter.get_XYZ('X')),
                        str(self.interpreter.get_XYZ('Y')),
                        str(self.interpreter.get_XYZ('Z'))] # updating last XYZ

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
        self.last_SP[0] = val
        
        val = int((self.interpreter.get_SP() - self.interpreter.get_SP()%256) / 256)
        SP_box.insert(END, f'  SPH: {val}\n')
        if val != self.last_SP[1]:
            SP_box.tag_add('SPH', '2.0', '3.0')
            SP_box.tag_configure('SPH', foreground=self.change_colour,background=self.text_bg)
        self.last_SP[1] = val

        val = hex(self.interpreter.get_SP())
        SP_box.insert(END, f'  SP: {val}')
        if val != self.last_SP[2]:
            SP_box.tag_add('SP', '3.0', '4.0')
            SP_box.tag_configure('SP', foreground=self.change_colour,background=self.text_bg)
        self.last_SP[2] = val

        SP_box.config(state=DISABLED)

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
        font_size = round(self.wh/85)

        console_box_title = Frame(self.root, bg=self.label_colour,height=frame_height,width=round(self.ww/6))
        console_box_title.place(x=otherx,y=othery+0.44*self.wh, anchor = 'n')

        console_box_label = Label(self.root,text='Console',font=(self.font,label_font_size),bg=self.label_colour,fg=self.label_text)
        console_box_label.place(x=otherx,y=othery+0.44*self.wh, anchor = 'n')

        self.console_box = Text(self.root,font=(self.font,font_size),height=16,width=27,bg=self.text_bg,fg=self.text_colour)
        self.console_box.config(borderwidth=5,relief='sunken')
        self.console_box.place(x=otherx, y=othery+0.48*self.wh, anchor = 'n')

    def buttons(self):
        
        x_val = 0.085 * self.ww

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
        clear_console_button.place(x=x_val,y=0.85*self.wh, anchor = 'n')

    def run(self):
        """
        Runs the whole code
        """
        while self.interpreter.file_end == False:
            output = self.interpreter.step()
            if isinstance(output, str):
                self.console_box.insert(END, output)
                self.console_box.yview_moveto(1)

            if isinstance(output, RETError):  # RET error
                self.console_box.insert(END, output)
                self.console_box.yview_moveto(1)
                break

        self.display()

    def step(self):
        step_size = self.step_box.get('1.0',END)
        try: step_size = int(step_size)
        except: step_size = 1
        for repeat in range(step_size):
            output = self.interpreter.step()
            if isinstance(output, str):
                self.console_box.insert(END, output)
                self.console_box.yview_moveto(1)
            if isinstance(output, RETError):  # RET error
                self.console_box.insert(END, output)
                self.console_box.yview_moveto(1)
                break
        
        self.display()

    def reset(self):
        """
        Resets the to be beginning so
        the file can be run again.
        """

        self.data = copy.deepcopy(self.data_copy)
        self.interpreter = Interpreter(self.data[0], self.data[1], self.data[2], self.data[3])

        self.display()

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

    def clear_console(self):
        self.console_box.delete('1.0', END)

    def convert_val_to_type(self, val, is_ram: bool):
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
            if (self.num_disp == 'TCOMP'): return val # dont do 2s comp on ram values, just do dec

        if self.num_disp == 'DEC':
            return str(val)

        if self.num_disp == 'BIN':
            if 0 <= val <= 255: n = 8
            if val > 255: n = 16
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
