# Punk Journal
***Software for Creating and Managing Cyberpunk RED Characters***

Punk Journal is software for creating and managing Cyberpunk Red Characters. It is a command line program that processes text files that describe how a character is build and equipped and produces a detailed and well organized PDF character sheet that can be printed out and used at the table. 

Punk Journal understands all of the rules for building Cyberpunk RED characters, all of the equipment in the Core Book, and a some of the gear found in the first years of DLC content. It strives to enforce all rules, and if a character builds successfully and without warnings, the player can reasonably assume their character is "street legal".

## Dependencies 
To successfully run Punk Journal, you will need to satisfy the following dependencies.

### System level dependencies
- [XeLaTeX](https://www.tug.org/texlive/) : Used by Punk Journal to produce PDF character files.
- [Font: Montserrat](https://fonts.google.com/specimen/Montserrat)
- [Font: Inconsolata](https://fonts.google.com/specimen/Inconsolata)

XeLaTeX and the Montserrat and Inconsolata fonts should be installed at the system level. XeLaTeX needs to be somewhere that the Punk Journal can find it on the system path. The fonts needs to be installed where XeLaTeX can find them; usually it is sufficient to install them at the operating system level with other fonts on the system.

### Python Dependencies 
- Python3
- PyYaml
- jinja2
- mistletoe

You will need a working Python3 interpreter and tool chain (pip) on your system. Installing python3 is operating system dependent, and there may be multiple options depending on your system. Any solution that gives you python3, virtual environments, and a pip should be sufficient to run Punk Journal as delivered.

The script mkpyenv.sh will create a virtual environment under the (hidden) directory .venv and install the required python packages into it. The run script pjournal will automatically invoke mkpyenv.sh if it doesn't not find the virtual environment. If you are simply running Punk Journal you will likely not have to worry about dependencies on python packages.

## Legal
Punk Journal is unofficial content provided under the [Homebrew Content Policy](https://rtalsoriangames.com/homebrew-content-policy/) of [R. Talsorian Games](https://talsorianstore.com/) and is not approved or endorsed by [R. Talsorian Games](https://talsorianstore.com/). This content references materials that are the property of [R. Talsorian Games](https://talsorianstore.com/) and its licensees.

The files found in the database directory are derived from material copyrighted R. Talsorian Games. They are made available under the previously mentioned [Homebrew Content Policy](https://rtalsoriangames.com/homebrew-content-policy/). They are explicitly not covered by the license for the rest of this software.

The Punk Journal software, including the python source, the documentation, the LaTeX support files, the templates, and everything not in the database directory, are covered by the Gnu Public License version 3.

Copyright 2024, Jason Denton