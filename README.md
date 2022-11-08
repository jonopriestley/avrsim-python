-------------------------------------------------------------------------------------------------------
AVR Simulator
-------------------------------------------------------------------------------------------------------
Simulator for AVR Instruction Set Architecture as taught in ELEC1601 at USyd. You do not need to understand the content of any of the code within the files here. There are a few things you will need for it to run properly.

- Requires Python to run
- If your Python does not come with Tkinter you will also need to install that

To run the file open a terminal window in the folder and run the sim.py file with:

python sim.py

-------------------------------------------------------------------------------------------------------
Key Commands:
<Esc>        -> quit
<Ctrl+R>     -> run whole file
<Ctrl+S>     -> step through code
<Ctrl+E>     -> reset to beginning
<Ctrl+C>     -> clear console
<Ctrl+U>     -> load updated file code
<Ctrl+N>     -> run a new file
-------------------------------------------------------------------------------------------------------
Code Theme (won't work on Mac, sorry)

If you wish to use the code theme to make your AVR code easier to navigate, I have provided an XML file that can be used in Notepad++. To use it, go to "Language > User Defined Language > Open User Defined Language Folder..." then put the file in that folder. It will then appear in the drop down list in the Language tab.
-------------------------------------------------------------------------------------------------------
Steps (for AVR.xml with dark mode)

- Download Notepad++
- Download the AVR.xml file
- Go to Language -> User Defined Language -> Open User Defined Language Folder, and put AVR.xml in that folder then reboot the app.
- Go to Settings -> Preferences -> Dark Mode, click Enable Dark Mode

Use the AVR language package for any AVR files you are writing.
-------------------------------------------------------------------------------------------------------
A Second Code Theme (for Mac)

If you download VS Code, you should be able to search for the extension "AVR Support". If you download that, you'll need to use .asm files instead of .txt files (just rename your files to .asm), but it will then colour some of your code to make it easier to read.
