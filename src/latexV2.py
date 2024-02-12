'''
	LaTexContext is a context manager for running LaTeX (and its derivates).

	When first created you may specify:
		latex_command: The command invoked by the latex method.
		destination: The directory where resulting files are placed. Defaults to the
			working directory when the LaTeXContext object is created.
		environment: A map of environmental variables to use when running the latex command.
			Defaults to the current environment.
		post_process: Defaults to true. See post processing below.

	When the context is opened it changes the working directory to a new temporary
	directory. When the context closes that directory and all its contents are deleted.
	While it exists the context can be evaluated as a string to determine the path of
	the temporary working directory.

	The latex method has the following parameters:
		filepath: name of the file to latex
		maxruns: Maximum runs of the latex command to perform. Defaults to 3.

	The latex method tries to be smart about the number of passes required, and will stop
	iterting when it detects that no further changes will be made by additional passes. It
	should be safe to set this value to an arbitraily high value if 3 passes is not enough.

	If post processing has been enabled (it is on by default), Ghostscript will be invoked
	in an attempt to compress the resulting PDF by discarding unneeded glyphs. This operation
	should not result in a quality loss, but it does result in any metadata set into the pdf
	by LaTeX being lost. Use the title, author, subject, keywords, and application methods
	to set values to be placed into the metadata during post processing. If post processing
	results in a larger file, that file will be discarded and the original file retained as
	the result of the latex method.

	When the latex method completes a file will be written to the destination directory.
	If the latex commanded succeed this will be the pdf file. If the command failed,
	the file will be named <basename>.err and contain the output of the LaTeX process
	command.

	After latex is run, you can test the boolean value of the context to determine if
	latex ran successfully and produced a pdf. it is possible to call latex multiple
	times from within the context. In this case only the most recent result is
	reflected in the boolean value of the context.

	Use the tex_input method to append another path to the tex_inputs environmental
	variable.

	Additional files can be copied to the designated destination directory with the 
	keep method.
'''

from datetime import datetime
import os
import shutil 
from subprocess import run
from tempfile import TemporaryDirectory, NamedTemporaryFile
from copy import copy 

class LaTeXContext:
	def _setmd(self, field):
		def _worker(self, k, v):
			self.metadata[k] = v 
		def wrapper(self, value):
			return _worker(field, value)
		return wrapper 

	def __init__(self, latex_command='pdflatex', destination=None, environment=None, post_process=True):
		if not shutil.which(latex_command):
			raise RuntimeError("The {} program is not available. Check to make sure it is installed and can be found on PATH.")
		self.latex_command = latex_command
		self.post_process = post_process
		self.working_dir = TemporaryDirectory()
		self.original_dir = os.getcwd()
		if not destination:
			self.destination = self.original_dir
		else:
			self.destination = destination
		self.latex_cmd = latex_command
		if environment:
			self.env = environment
		else:
			self.env = copy(os.environ)
		self.metadata = {
			'title':None, 
			'author':None, 
			'subject':None, 
			'keywords':None, 
			'application':None
		}
		self.success = False

		#setup functions to set metadata
		for k in self.metadata.keys():
			self.__setattr__(k,self._setmd(k))

	def __enter__(self):
		os.chdir(self.working_dir.name)
		return self

	def __exit__(self, kind, value, traceback):
		os.chdir(self.original_dir)
		del self.working_dir

	def __str__(self):
		return self.working_dir.name

	def __bool__(self):
		return self.success

	def _set_file_names(self, latex_filename):
		base_name = os.path.basename(latex_filename.replace('.tex',''))
		self.file2tex = latex_filename
		self.pdf_name = base_name + '.pdf'
		self.stdout_name = base_name + '.stdout'

	def _run_latex(self, maxruns):
		found = 1
		runs = 0
		while found != -1 and runs < maxruns:
			proc = run([self.latex_command, '-halt-on-error', 
				'-interaction=nonstopmode', self.file2tex], env=self.env, capture_output=True, text=True)
			if proc.returncode:
				break
			found = proc.stdout.find('Label(s) may have changed')
			runs += 1
		if proc.returncode:
			if os.path.exists(self.pdf_name):	
				os.unlink(self.pdf_name)
			with open(self.stdout_name,'w') as fout:
				fout.write(proc.stdout)
			self.success = False 
		else:
			self.success = True

	def _setup_metadata(self):
		dstring = datetime.now().strftime("(D:%y%m%d%H%M%S)")
		with open('._metadata', 'w') as fout:
			fout.write("[ ")
			if self.metadata['title']:
				fout.write("/Title (%s)\n" % self.metadata['title'])
			if self.metadata['author']:
				fout.write("/Author (%s)\n" % self.metadata['author'])
			if self.metadata['subject']:
				fout.write("/Subject (%s)\n" % self.metadata['subject'])
			if self.metadata['keywords']:
				if (isinstance(self.metadata['keywords'], list)):
					self.metadata['keywords'] = ', '.join(self.metadata['keywords'])
				fout.write("/Keywords (%s)\n" % self.metadata['keywords'])
			fout.write("/ModDate %s\n" % dstring)
			fout.write("/CreationDate %s\n" % dstring)
			if self.metadata['application']:
				fout.write("/Creator (%s)\n" % self.metadata['application'])
			fout.write("/Producer (PDFTeX)\n/DOCINFO pdfmark\n")

	def _post_process(self):
		cfile = '_X_TMP_X_.pdf'
		cmdline = ['gs', '-sDEVICE=pdfwrite','-dCompatibilityLevel=1.4', '-dPDFSETTINGS=/printer', '-dNOPAUSE', 
		'-dQUIET', '-dBATCH', '-sOutputFile=%s' % cfile, self.pdf_name, '._metadata']
		proc = run(cmdline, capture_output=True, text=True)
		if proc.returncode:
			with open(self.stdout_name,'w') as fout:
				fout.write(proc.stdout)
			self.success = False
		elif os.path.getsize(self.pdf_name) >= os.path.getsize(cfile):	
			os.unlink(pdffile)
			os.rename(cfile, self.pdf_name)

	def tex_inputs(self, path):
		tin = self.env.get('TEXINPUTS','.:')
		if tin[-1] != ':':
			tin += ':'
		tin += path
		tin += ':'
		self.env['TEXINPUTS'] = tin

	def keep(self, filename):
		shutil.copy(filename, self.destination)

	def keep_as(self, filename, newname):
		shutil.copy(filename, path.os.join(self.destination,newname))

	def named_tmp_file_with_data(self, data):
		fname = None
		with NamedTemporaryFile(dir=self.working_dir, delete=False) as fout:
			fname = fout.name 
			fout.write(data)
		return fname

	def save_data_to_file(self, fname, data):
		with open(fname, 'w') as fout:
			fout.write(data)

	def latex(self, fpath, maxruns=3):
		self._set_file_names(fpath)
		self._run_latex(maxruns)
		if self.post_process: 
			self._setup_metadata()
			#self._post_process()
		if (self.success):
			self.keep(self.pdf_name)
		else:
			self.keep(self.stdout_name)

class XeLateXContext(LaTeXContext):
	def __init__(self, *args, **kwargs):
		super().__init__(latex_command='xelatex', *args, **kwargs)

