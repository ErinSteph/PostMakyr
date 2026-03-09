# PostMakyr

Automatically patch your mod project to run makyr on build.

[Download](https://github.com/ErinSteph/PostMakyr/raw/refs/heads/main/PostMakyr.exe)

<img width="700" alt="PostMakyr" src="https://github.com/user-attachments/assets/d974407d-2fe3-4dbb-8f0c-e1de24d5d91d" />

- close visual studio if you have your project open
- make sure maykr.exe and your *_makyr.kmc file are inside your mod project folder
- open PostMakyr, hit browse, select your project folder
- make sure the path to the CarX mods folder is accurate
- hit scan
- hit Apply To Selected Project

Next time you build your project in visual studio, it should automatically build the .ksm file with makyr and copy it to the mods folder, so after a succesful build, you can instantly launch CarX.





## Building from src

`pip3 install pyinstaller dearpygui`

`pyinstaller --onefile --windowed --name PostMakyr --icon PostMakyr.ico PostMakyr.py`
