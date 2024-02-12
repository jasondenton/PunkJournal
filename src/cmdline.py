#!env python3
from pjournal import MakePunk, MakePDFSheet
import sys 
from character import CharacterFile
import os 
import json 

from argparse import ArgumentParser

def read_cmdline():
	parser = ArgumentParser(description='Punk Journal: Character Software for Cyberpunk RED')
	parser.add_argument('Files', nargs='+', type=str, help='First file must be the character build log; should have a .txt or .cpred extension.\nNext file is the character portrait (optional).')
	parser.add_argument('-nologs', dest='logs', action='store_false', default=True,
		help='Prevent logs (bank, xp, humanity) from appearing in the PDF.')
	parser.add_argument('-npc', dest='master_template', action='store_const',
		const='concise', default='default', help="Force concise format (1 page NPC format).")
	parser.add_argument('-pc', dest='master_template', action='store_const',
		const='complete', default='default', help="Force complete format (PC format).")
	parser.add_argument('-a4', dest='paper_size', action='store_const',
		const='a4', default='letter', help="Use A4 Paper instead of letter size.")
	parser.add_argument('-json', dest='json', action='store_true', default=False,
		help='Dump a JSON version of the character data.')
	parser.add_argument('-tex', dest='tex', action='store_true', default=False,
		help='Write out the XeLaTeX source used to generate the PDF.')
	args = parser.parse_args()
	return args

def print_warnings(warnings):
	if not len(warnings): 
		return
	print('================================================================================')
	for warn in warnings:
		print('{:03d}\t{:s}'.format(warn['line'], warn['message']))
	print('================================================================================')

def filenames(flst):
	fpath = flst[0]
	(fdir, fname) = os.path.split(fpath)
	bname = fname.replace('.cpred','')
	bname = bname.replace('.txt','')
	#bname = os.path.join(fdir,bname)
	if len(flst) > 1:
		pname = flst[1]
		if pname[0] != '/':
			pname = os.path.join(os.getcwd(),pname)
	else:
		pname = False

	return {
		'input' : fpath,
		'pdf' : bname + '.pdf',
		'dump' : bname + '.json',
		'tex' : bname + '.tex',
		'portrait' : pname,
	}

def main():
	args = read_cmdline()
	try:
		files = filenames(args.Files)
		charrec = CharacterFile(files['input'])
		punkdata = MakePunk(charrec)
		punkdata['portrait'] = files['portrait']
		punkdata['logs'] = punkdata.get('logs', args.logs)
		punkdata['sheet'].update({
			'master_template' : args.master_template,
			'logs' : args.logs,
			'paper_size' : args.paper_size,
		})
		if punkdata['sheet']['master_template'] == 'default':
			punkdata['sheet']['master_template'] = punkdata['sheet']['default']
		if args.json:
			with open(files['dump'],'w') as fout:
				fout.write(json.dumps(punkdata, indent=4))
		print_warnings(punkdata['warnings'])
		MakePDFSheet(files['tex'], punkdata,master_template='root',save_latex=args.tex)

	except RuntimeError as rex:
		print(str(rex))

main()
