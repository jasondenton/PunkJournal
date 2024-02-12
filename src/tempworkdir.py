from tempfile import TemporaryDirectory
import os 

class TemporaryWorkingDirectory(TemporaryDirectory):
	def __init__(self):
		super().__init__()
		self.original = os.getcwd()

	def __enter__(self):
		super().__enter__()
		os.chdir(self.name)
		return self 
		
	def __exit__(self, kind, value, traceback):
		super().__exit__(kind, value, traceback)
		os.chdir(self.original)