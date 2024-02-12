from collections import UserDict
from ledger import BankAccount
from inventory import CharacterInventory
from cbexception import CharacterBuilderBadCommand

class CharacterRecord:
	def __init__(self, data):
		#gah, fix DOS files.
		self.data = [d.replace('\r\n', '\n') for d in data]

		self.setname()
		self.setnotes()
		if len(self.data) < 1:
			raise RuntimeError('Empty Character File.')
		
	def setname(self):
		idx = 0
		while idx < len(self.data) and (self.data[idx][0] == '#' or len(self.data[idx].strip()) == 0):
			idx += 1
		if idx == len(self.data) or self.data[idx][0:3] == '---' or self.data[idx][0:3] == '===':
			raise cbe.CharacterBuilderBadCommand(cbe.BADFILE)
		self.name = self.data[idx].replace('\n','')
		if '#' in self.name:
				self.name = self.name[0:self.name.index('#')].strip()
		self.name_line = idx+1
		self.firstbuild = idx+1

	def setnotes(self):
		idx = self.firstbuild
		while idx < len(self.data) and self.data[idx][0:3] != '===':
			idx += 1
		self.notes = ''.join(self.data[idx+1:])
		self.lastbuild = idx - 1

	@staticmethod
	def is_blank(line):
		tst = line.replace(' ','')
		tst = line.replace('\t','')
		tst = line.replace('\n','')
		if len(tst) < 1:
			return True
		return False

	def readbuild(self):
		idx = self.firstbuild
		while idx <= self.lastbuild:
			while idx <= self.lastbuild and (len(self.data[idx]) and self.data[idx][0] == '#' or self.is_blank(self.data[idx])):
				idx += 1
			if idx > self.lastbuild: break
			retline = self.data[idx]
			if '#' in self.data[idx]:
				retline = retline[0:retline.index('#')].strip()
			self.original_case = retline.replace('\n','').strip()
			retline = self.original_case.lower()
			yield (idx+1, retline)
			idx += 1

class CharacterFile(CharacterRecord):
	def __init__(self, fpath):
		with open(fpath) as fin:
			data = fin.readlines()
		super().__init__(data)

class CharacterStream(CharacterRecord):
	def __init__(self, fin):
		data = fin.readlines()
		clean = []
		for d in data:
			clean.append(d.decode('utf-8', 'ignore'))
		super().__init__(clean)
		
class CharacterPostBody(CharacterRecord):
	def __init__(self, cdat):
		data = cdat.decode('utf-8', 'ignore').split('\n')
		self.debug = len(data)
		super().__init__(data)

class BaseCharacter(UserDict):
	def __init__(self, inventory=False, bank=False):
		super().__init__(self)
		self.name = 'Anon y Mous'
		self.title = None
		self.gender = None
		self.portrait = None
		self.token = None
		self.date = None
		self.creation_finished = False
		self.warnings = []
		if not bank:
			self.bank = BankAccount()
		else:
			self.bank = bank 
		if not inventory:
			self.inventory = CharacterInventory()
		else:
			self.inventory = inventory
		self.token_size = (1,1)

	def set_date(self, date):
		self.date = date 
		self.bank.date = date
		
	def get_inventory(self):
		return self.inventory.by_location()

	def add_item(self, itm, num=1, location='carried'):
		self.inventory.add(itm,num,location)

	def remove_item(self, key, num=1, location='carried'):
		self.inventory.remove(key,num,location)

	def end_creation(self):
		self.creation_finished = True

	def build_finished(self):
		if not self.creation_finished:
			self.end_creation()






	
