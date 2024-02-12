To run Punk Journal from the command line in a Unix like environment, use the command
`pjournal <character file> [portrait.jpg]`. This shell script sets up the required runtime environment and invokes the command line program.

The character file should be a valid Punk Journal build record. You can find some examples in the *examples directory*. The file example/blank.txt is a good place to start customizing to create your first character. The contents of the *doc* directory explain the full format and syntax for character build records.

A portrait file is optional, and must be a JPEG or PNG formatted file. Recommended size is 256x256 pixels.

Run the command  `pjournal -h` to get a help message explaining all the options supported by Punk Journal.

Use the `-json` option to get a JSON formatted dump of the data used to create the character sheet. This option might be useful if you are using Punk Journal to process a character before sending the results to another piece of software.

Use the `-tex` option to save a copy of the LaTeX source used to generate the PDF.

Use the `-a4` option to have the resulting PDF be formatted for A4 paper instead of US letter sized paper.

Use the `-pc/-npc` for force a processed character sheet to use the long form PC sheet or concise NPC format.

Use `-nologs` to suppress detailed bank/IP/humanity records when producing a PC character sheet.