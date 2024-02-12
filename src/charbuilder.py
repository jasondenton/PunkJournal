from re import IGNORECASE
from patterns import PatternExecutor
from cbexception import CharacterBuilderBadCommand

NOTUNDERSTOOD = {
	'code' : 9999,
	'message' : 'Command not understood.' 
}
NOTENOUGHCASH = {
	'code' : 101,
	'message' : 'Not enough cash to buy {item}.'
}
NOTFORSALE = {
	'code' : 102,
	'message' : '{item} is not for sale.'
}

class BaseCharacterBuilder:

	def portrait(self, fields):
		self.character.portrait = fields['path']

	def token(self, fields):
		self.character.token = fields['path']		
		
	def title(self, fields):
		self.character.title = self.buildrec.original_case[6:]

	def noop(self, fields):
		pass

	def _pragma(self, fields):
		self.pragma(fields['pragma'].lower())

	def literal(self, fields):
		lit = fields['literal']
		if lit in self.literals:
			self.literals[lit](lit)
		else:
			self.unknown_line(lit)

	def end_creation(self, fields):
		self.character.end_creation()
		self.creation_done = True

	def gender(self, gender):
		self.character.gender = gender.capitalize()

	def character_value(self, fields):
		self.character.values[fields['key']].value = int(fields['value'])

	def decode_inventory_field(self, fields):
		name = fields['name'].strip().lower()
		cnt = fields.get('count', 1)
		if not cnt: count = 1
		else: count = int(cnt)
		itm = self.character.inventory.local_item_descriptor(name)
		if not itm:
			itm = self.marketdb[name]
		return (name, itm, count)

	def add_item(self, itm, count=1, location=None):
		self.character.add_item(itm, count, location)

	def remove_item(self, key, count=1, location='carried'):
		self.character.remove_item(key, count, location)

	def buy_package(self, p):
		pkg = [self.marketdb[i] for i in p.package]
		cost = sum([i.cost for i in pkg])
		loc = p.get('sendto', None)
		if not self.character.bank.can_afford(cost):
			raise CharacterBuilderBadCommand(NOTENOUGHCASH,item=p.name)
		for i in pkg:
			self.add_item(i, 1, loc)
		self.character.bank.add_entry(-cost, 'Bought {}'.format(p.name))	

	def find_package(self,p): 			
		pkg = [self.marketdb[i] for i in p.package]
		for i in pkg:
			self.add_item(i, 1, 'carried')

	def buy(self, fields):
		(key, itm, count) = self.decode_inventory_field(fields)
		if itm.package:
			self.buy_package(itm)
			return itm
		if itm.cost == -1: 
			raise CharacterBuilderBadCommand(NOTFORSALE,item=itm.name)
		cost = itm.cost * count * -1.0
		if count == 1:
			num_memo = ''
		else: num_memo = '{} '.format(count)
		#bank ledger does knows the balance, and so does the cost check and raise on insufficent cash
		self.character.bank.add_entry(cost, 'Bought {}{}'.format(num_memo, str(itm)), itm)
		if not 'service' in itm.get('keywords',[]):
			count *= itm.get('count', 1)
			self.add_item(itm, count)
		return itm

	def find(self, fields):
		(key, itm, count) = self.decode_inventory_field(fields)
		if itm.get('package', False):
			self.find_package(itm)
			return
		self.add_item(itm, count)	

	def move(self, fields):
		(key, itm, count) = self.decode_inventory_field(fields)
		frm = fields.get('from', 'carried').strip()
		to = fields.get('to', 'carried').strip()
		self.remove_item(key, count, frm)
		self.add_item(itm, count, to)

	def drop(self, fields):
		(key, itm, count) = self.decode_inventory_field(fields)
		frm = fields.get('from', 'carried').strip()
		self.remove_item(key, count, frm)

	def sell(self, fields):
		(key, itm, count) = self.decode_inventory_field(fields)
		frm = fields.get('from',False)
		if not frm:
			frm = self.character.inventory.find(key,count)
		if not frm: frm = 'carried'
		self.remove_item(key, count, frm)
		price = itm.value * count
		if count == 1:
			num_memo = ''
		else: num_memo = ' {} '.format(count)
		self.character.bank.add_entry(price, 'Sold {}{}'.format(num_memo, str(itm)))

	def loot(self,fields):
		(key, itm, count) = self.decode_inventory_field(fields)
		price = itm.value * count
		if count == 1:
			num_memo = ''
		else: num_memo = ' {} '.format(count)
		self.character.bank.add_entry(price, 'Looted {}{}'.format(num_memo, str(itm)))

	def designate(self, fields):
		item = fields['item'].lower()
		tag = fields['tag'].lower()
		return self.character.inventory.designate(item, tag)

	def attach(self, fields):
		att = fields['attachment'].lower().strip()
		host = fields['host'].lower().strip()
		self.character.inventory.attach(host, att)

	def set_date(self, fields):
		self.character.set_date(fields['date'])

	def bank(self, fields):
		if fields['sign'] == '-':
			sign = -1.0
		else:
			sign = 1.0
		amt = float(fields['amount']) * sign
		self.character.bank.add_entry(amt, fields['memo'].capitalize())
		 
	#override to provide @ commands
	def pragma(self, p):
		pass

	#return a map of literals->function.
	#where literal is a non-regex string to be matched, and
	#f(literal) is a function which takes a copy of the string.
	#Over ride to provide per game system processing
	def literal_functions(self):
		return {}

	# return a list of rules to be checked before the base rules.
	# each rule is a of the form [rule,func], where rules is a regex string
	# using ?>P<field> syntax, and func is a defines as func(self, fields)
	def more_rules(self):
		return []

	def unknown_line(self, line):
		raise CharacterBuilderBadCommand(NOTUNDERSTOOD)

	def token_size(self, fields):
		w = int(fields['width'])
		l = int(fields['length'])
		self.character.token_size = (w,l)

	def __init__(self):
		#implementation must define
		#self.character
		#self.makertdb
		rules = [
			['^\s*$', self.noop],
			['^@(?P<pragma>.*)$', self._pragma],
			['^portrait (?P<path>.*)', self.portrait],
			['^token (?P<path>.*)', self.token],
			['^title (?P<title>.*)', self.title],
			['^---', self.end_creation],
			['buy\s(?P<count>\d*)?\s?(?P<name>.*)', self.buy],
			['found\s*(?P<count>\d*)?\s?(?P<name>.*)', self.find],
			['move\s(?P<count>\d*)?\s?(?P<name>.*)\sfrom\s(?P<from>.*)?\sto\s(?P<to>.*)', self.move],
			['move\s(?P<count>\d*)?\s?(?P<name>.*)\sto\s(?P<to>.*)', self.move],
			['move\s(?P<count>\d*)?\s?(?P<name>.*)\sfrom\s(?P<from>.*)', self.move],
			['drop\s(?P<count>\d*)?\s?(?P<name>.*)\sfrom\s(?P<from>.*)', self.drop],
			['drop\s(?P<count>\d*)?\s?(?P<name>.*)', self.drop],
			['sell\s(?P<count>\d*)?\s?(?P<name>.*)\sfrom\s(?P<from>.*)', self.sell],
			['sell\s(?P<count>\d*)?\s?(?P<name>.*)', self.sell],
			['loot\s(?P<count>\d*)?\s?(?P<name>.*)', self.loot],
			['tag\s(?P<item>.*)\sas\s(?P<tag>.*)', self.designate],
			['attach\s(?P<attachment>.*)\sto\s(?P<host>.*)',self.attach],
			['date\s(?P<date>\d\d\d\d\-\d\d?-\d\d?)',self.set_date],
			['size\s(?P<width>\d+)x(?P<length>\d+)', self.token_size],
			['(?P<sign>[+-])?\$(?P<amount>[+-]?\d+\.?\d?\d?)\s+(?P<memo>.*)?', self.bank],
			['^(?P<key>.*)\s(?P<value>\d+)', self.character_value],
			['^(?P<literal>.*)$', self.literal]
		]
		self.date = ''

		self.literals = {
			'male' : self.gender,
			'female' : self.gender,
			'non-binary' : self.gender
		}

		self.exec = PatternExecutor(self.more_rules() + rules, IGNORECASE)
		self.literals.update(self.literal_functions())
		self.creation_done = False
		self.build_done = False


	# buildrec must honor the build record contract;
	# the build record contract is whatever build_character needs.
	# For example, a character file.
	def build_character(self, buildrec):
		#if len(buildrec.name.strip()) == 0:
		#	self.character.warnings.append({
		#		'code' : 1, 
		#		'line' : buildrec.name_line, 
		#		'message' : 'First non-comment line should be the character name, but that line is blank.'})
		#else:
		self.character.name = buildrec.name
		self.character.notes = buildrec.notes
		self.buildrec = buildrec 
		for (lineno, line) in buildrec.readbuild():
			try:
				if not self.exec.process_line(line):
					self.unknown_line(line)
			except CharacterBuilderBadCommand as ex:
				dump = ex.dump()
				dump['line'] = lineno
				self.character.warnings.append(dump)
		self.character.build_finished()
		return self.character

