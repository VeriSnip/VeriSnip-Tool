## Overview
My Verilog Template is a project that I will be working on my free time. The project aim is to compile and elaborate Verilog modules. The Verilog cores are written in traditional Verilog and might use `include "file" to add automaticaly generated code.

### Index
1. [How to use MyVT](#how-to-use-myvt)
2. [Development Environment](#development-environment)
3. [Scripts](#scripts)
    1. [VTbuild.py](#vtbuild)
    2. [VTmodule.py](#vtmodule)
4. [Glossary](#glossary)
5. [Contributing](#contributing)
6. [Credits](#credits)

## How to use MyVT
Using "MyVT" will create a build directory where all the RTL code needed to build the core can be found. The first step to do so is calling the "VTbuild" script.
### Calling VTbuild
The main Makefile of the project should define the project name and call the "VTbuild" script. The project name will be use to find the core top module, as it should be the "project name".\[v/vs\] and the top test-bench which should be "project name"\_tb\_.\[v/vs/cpp\].

### Using or Creating scripts
Users can create custom scripts that generate ".vs" files or Verilog modules or use those that are already existent. Any scripting language can be used.  All scripts which generate Verilog code (be it modules or ".vs" files) are independent from "VTbuild". Therefor, "VTbuild" only calls the scripts and does not import them.

## Development Environment
...

### Nix
Run `nix-shell` with the "shell.nix" of this repository to enter a development environment that automatically installs and manages the tools commonly needed by the projects.

## Scripts
...

### VTbuild
- "VTbuild" starts by looking for the Verilog top module. The script initially only knows that it needs the top module file. It then starts to:
	-  First, locate where the files needed are and copy them to the build directory. If the files do not exist it will look for and call the scripts witch can generate them.
	- Second, the script finds all the Verilog modules or ".vs" files included in the files it needs.
	- Third, repeat the first and second step until no additional files are added.

#### Calling the scripts
- When calling scripts to generate ".vs" priority is always given to scripts with the full name of the file. If there is no script curresponding to the ".vs" name look for a script that currsponds only to the inicial part of the name. Example:
	- in `include "io_modules.vs"` look for `VTio.py` or `io.py` if `io_modules.py` does not exist.
- When calling scripts that generate modules the script should have the name of the module.
- "VTbuild" only calls the scripts if they are newer then the files already existent.
- When there are two or more scripts with the same name a warning should be printed and the script with the closest directory path should be used. 
- All files and scripts should only be looked for from the base directory of the project, unless specified otherwise in a custom script.

#### Copy files
- all files which are generated should have a copy in the "aux" directory
- "VTbuild" substitutes the ".vs" and copies the modules needed to the build directory, after finding or generating all modules and ".vs" files.

#### bla


### VTmodule
This script defines a python class which may be used by the user. This class should help create a systematic way of generating repetitive Verilog code in different components.
#### Class variables
#### Class methods
#### Example

## Glossary
- vt - Verilog Template
- vs - Verilog Snippet
### Verilog code style
- \_i - input
- \_o - output
- \_r - registed
- \_e - enable
- \_n - next
- ...

## Contributing
People may contribute with automatic generated verilog scripts. These scripts should be under the hardware/scripts directory. Furthermore, when adding a script the contributer must as well write a corresponding section on the README. That section should explain the core generated and how the script should be used. The section structure must follow the other scripts sections structures.

## Credits
This project idea came to me while I was working at IObundle. IObundle was developing a similar open-source tool called python-setup. 

The two projects are fundamentally different. Therefore I decided to create this project from 0 instead of contributing the ideas and tools directly to IObundle's python-setup.

Where the two projects are similar is both are being developed to generate automatic verilog. 

Where they mainly differ is on the way the verilog is generated. The IObundle python-setup project aims to generate all the verilog core using a python framework. MyVerilogTemplate aims to substitute the .vs files present on the verilog code. Generating the .vs code as needed. There may also exist scripts that generate .v modules.
