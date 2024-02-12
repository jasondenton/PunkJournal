from copy import copy
from tempfile import mkstemp
import shutil 
import os 

from character import CharacterRecord
from CPBuilder import CyberpunkCharacterBuilder
from CPCharacter import CyberpunkPCCharacter, CyberpunkNPCCharacter, CyberpunkAnimalCharacter, CyberpunkQuickCharacter
from jinja2_helper import LaTeXTemplateEngine
from latexV2 import XeLateXContext
from patterns import PatternExecutor
from re import IGNORECASE

class CPPreScan(PatternExecutor):
	def __init__(self):
		self.npc_mode = False 
		self.total_mode = False 
		self.animal_mode = False
		self.quick_mode = False
		rules = [
			['^npc$', self.npc],
			['^mook$', self.total],
			['^animal$', self.animal],
			['^quick$', self.quick]
		]
		super().__init__(rules, flags=IGNORECASE)

	def total(self, *args, **kwargs):
		self.npc_mode = True 
		self.total_mode = True

	def npc(self, *args, **kwargs):
		self.npc_mode = True 

	def animal(self, *args, **kwargs):
		self.npc_mode = True
		self.animal_mode = True

	def quick(self, *args, **kwargs):
		self.npc_mode = True 
		self.quick_mode = True

	@staticmethod
	def scan(buildrec):
		scanner = CPPreScan()
		for line in buildrec.readbuild():
			scanner.process_line(line[1])
		return scanner

def setup_latex():
	global latex_asset_path
	lenv = copy(os.environ)
	tin = '.:' + latex_asset_path + ':'
	if 'TEXINPUTS' in lenv:
		tin += lenv['TEXINPUTS']
	lenv['TEXINPUTS'] = tin 
	return lenv

def MakePDFSheet(template_data, master_template='root', save_latex=False):
	global tmp_path 
	global latex_environment
	pdf_text = latex_template_engine.Render(template_data, master_template)
	(tex_handle, tex_file) = mkstemp(suffix='.tex', prefix='pjrnl_', dir=tmp_path, text=True)
	with open(tex_handle, 'w') as fout:
		fout.write(pdf_text)
	(success, result) = LaTeX2PDF(tex_file,maxruns=2, compress=False, env=latex_environment)
	if save_latex:
		shutil.move(tex_file, save_latex)
	else:
		os.unlink(tex_file)
	if not success:
		if save_latex:
			shutil.move(result, save_latex.replace('.tex','.err'))
		raise RuntimeError('Failed to create PDF.')
	return result

def MakePDFSheet(texsrcfname, template_data, master_template='root', save_latex=False):
	global tmp_path 
	global latex_environment
	tex_text = latex_template_engine.Render(template_data, master_template)
	#if save_latex:
	#	with open(texsrcfname, 'w') as fout:
	#		fout.write(tex_text)
	try:
		with XeLateXContext(post_process=False) as lcontext:
			lcontext.save_data_to_file(texsrcfname, tex_text)
			lcontext.latex(texsrcfname)
			if save_latex:
				lcontext.keep(texsrcfname)

	except RuntimeError as rt:
		print('Could not find XeLaTeX, which is required to produce PDF character sheets.')
		print('No PDF produced. ')

def MakeCharacter(charrec):
	pre = CPPreScan.scan(charrec)
	if not pre.npc_mode:
		csheet = CyberpunkPCCharacter()
	elif pre.animal_mode:
		csheet = CyberpunkAnimalCharacter()
	elif pre.quick_mode:
		csheet = CyberpunkQuickCharacter()
	else:
		csheet = CyberpunkNPCCharacter()
	builder = CyberpunkCharacterBuilder(csheet, pre.total_mode)
	character = builder.build_character(charrec)
	del builder
	return character

def MakePunk(charrec):
	character = MakeCharacter(charrec)
	template_data = character.render()
	return template_data


db_path = os.environ['PUNKJOURNALDB']
template_path = os.environ['PUNKJOURNALTEMPLATES']
tmp_path = os.environ['PUNKJOURNALTMP']
latex_asset_path = os.environ['PUNKJOURNALLATEX']
latex_template_engine = LaTeXTemplateEngine(template_path)
latex_environment = setup_latex()

try:
	os.makedirs(tmp_path)
except:
	pass
