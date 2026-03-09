# PostMakyr

Automatically patch your mod project to run makyr on build.

- make sure maykr.exe and you *_makyr.kmc file are inside your mod project folder
- open PostMakyr, hit browse, elect your project folder
- make sure the path to the CarX mods folder is accurate
- hit scan
- hit Apply To Selected project

Next time you build your project in visual studio, it should automatically build the .ksm file with makyr and copy it to the mods folder, so on osuccesful build, you can instantly launch CarX.





## Building from src

`pip3 install pyintaller dearpygui tkinter`

`pyinstaller --onefile --windowed --name PostMakyr --icon PostMakyr.ico PostMakyr.py`