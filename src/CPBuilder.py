from charbuilder import BaseCharacterBuilder, NOTUNDERSTOOD
from CPCharacter import CyberpunkPCCharacter
from CPGear import CyberpunkMarket
from cbexception import CharacterBuilderBadCommand
from utils import add_argument

NOSUCHVALUE = {
	'code' : 2034,
	'message' : 'No such character value as {value}.'
}

NOPACKHAGGLE = {
	'code' : 2024,
	'message' : 'You can not haggle for item bundles.'
}

NOTAFIXER = {
	'code' : 2111,
	'message' : 'Only fixers may haggle.'
}

CANNOTMAKE = {
	'code' : 2351,
	'message' : 'You cannot make a {item}.'
}

DONTKNOWMAKE = {
	'code' : 2723,
	'message' : 'You do not know how to make {item}.'
}

BADTOTAL = {
	'code' : 2346,
	'message' : 'A value of {final} for {skill} is less than the relavent stat {stat}.'
}

class CyberpunkCharacterBuilder(BaseCharacterBuilder):
	def __init__(self, csheet=None, mode=False):
		if csheet == None:
			self.character = CyberpunkPCCharacter()
		else:
			self.character = csheet
		self.marketdb = CyberpunkMarket
		super().__init__()
		self.tech_make = set(['weapon', 'armor', 'gear', 'cyberdeck', 'shield', 'ammunition'])
		self.make_reject = set(['cyberware', 'borgware', 'service'])
		self.total_mode = mode

	def more_rules(self):
		return [
			['^humanity\s(?P<amount>[+-]?\d*)\s?(?P<memo>.*)?', self.humanity_event],
			['^remove\s(?P<name>.*)', self.remove],
			['^swap\s(?P<side>(left|right))\s*(?P<borg>(borg\s*)?)arm\s*for\s*(?P<spare_name>.*)', self.swap_arms],
			['^slot\s(?P<chip>.*)', self.slot_chip],
			['^improve\s(?P<value>.*)', self.improve],
			['^session\s(?P<ip>\d*) (?P<memo>.*)', self.game_session],
			['^grease\s(?P<language>.*)', self.grease_add_lang],
			['^haggle\s(?P<count>\d*)?\s?(?P<name>.*)', self.haggle],
			['^upgrade\s(?P<utype>[A-Za-z]*)\s*on\s*(?P<tag>.*)', add_argument(self.upgrade, False)],
			['^\$upgrade\s(?P<utype>[A-Za-z]*)\s*on\s*(?P<tag>.*)', add_argument(self.upgrade, True)],
			['^learn\s*(?P<subject>.*)', self.learn],
			['^make\s*(?P<item>.*)', self.make],
			['^moto\s(?P<value>\d\d?)$', self.moto_kludge],
			['^moto\s(?P<item>.*)', self.moto],
			['^npc$', self.noop],
			['^mook$', self.noop],
			['^animal$', self.noop],
			['^quick$', self.noop],
			['^combat number\s(?P<cn>\d*)', self.combat_number]
		]

	def moto_kludge(self, fields):
		self.character_value({'key' : 'moto', 'value' : fields['value']})

	def unknown_line(self, line):
		try:
			self.buy({'name' : line, 'count' : 1})
		except CharacterBuilderBadCommand as cbe:
			raise CharacterBuilderBadCommand(NOTUNDERSTOOD)

	def learn(self, fields):
		self.character.values['pharmaceuticals'].learn(fields['subject'])

	def moto(self, fields):
		itm = self.marketdb[fields['item']]
		self.character.values['moto'].moto(itm)

	def make(self, fields):
		count = 1
		itm = self.marketdb[fields['item']]
		if len(self.make_reject & itm.keywords) > 0:
			raise CharacterBuilderBadCommand(CANNOTMAKE, item=str(itm))
		if 'pharma' in itm.keywords:
			psk = self.character.values['pharmaceuticals']
			if not itm.name.lower() in psk.known_recipies:
				raise CharacterBuilderBadCommand(DONTKNOWMAKE, item=itm.name)
			count = self.character.values['Medical Tech'].value
			cost = 200
		elif len(self.tech_make & itm.keywords) > 0:
			tsk = self.character.values['fabrication expertise']
			if tsk.value < 1:
				raise CharacterBuilderBadCommand(DONTKNOWMAKE, item=itm.name)
			cost = itm.cost / 2.0 
		else:
			raise CharacterBuilderBadCommand(CANNOTMAKE, item=str(itm))
		if count == 1:
			num_memo = ''
		else: num_memo = '{} '.format(itm.count)
		self.character.bank.add_entry(cost*-1.0, 'Made {}{}'.format(num_memo, str(itm)), itm)
		self.add_item(itm, count, 'carried')
		return itm

	def upgrade(self, payfor, fields):
		utype = fields['utype'].lower()
		tag = fields['tag'].lower()
		if payfor:
			if not tag in self.character.inventory.designated:
				raise CharacterBuilderBadCommand(NOSUCHDESIGNATION, loc=tag)
			itm = self.character.inventory.designated[tag]
			self.character.bank.add_entry(-itm.cost,'Upgrade {} on {}.'.format(utype, str(itm)))
		itm = self.character.inventory.upgrade(tag, utype)
		return itm

	def haggle(self, fields):
		opsk = self.character.values['operator']
		if opsk.value == 0:
			raise CharacterBuilderBadCommand(NOTAFIXER)
		(key, itm, count) = self.decode_inventory_field(fields)
		if itm.package:
			raise CharacterBuilderBadCommand(NOPACKHAGGLE)
		if itm.cost == -1: 
			raise CharacterBuilderBadCommand(NOTFORSALE,item=itm.name)
		discount_cost = itm.cost * (1.0 - (opsk.discount / 100.0)) * count  
		freebies = count // 5
		freebie_cost = (count - freebies) * itm.cost 
		totalcost = min(discount_cost, freebie_cost)
		if count == 1:
			num_memo = ''
		else: num_memo = ' {} '.format(count)
		#bank ledger does knows the balance, and so does the cost check and raise on insufficent cash
		self.character.bank.add_entry(-totalcost, 'Haggled for {}{}'.format(num_memo, str(itm)), itm)
		if not 'service' in itm.get('keywords',[]):
			count *= itm.get('count', 1)
			self.add_item(itm, count, 'carried')
		return itm

	def grease_add_lang(self, fields):
		self.character.values['operator'].grease_language(fields['language'])

	def improve(self, fields):
		vname = fields['value']
		if not vname in self.character.values:
			raise CharacterBuilderBadCommand(NOSUCHVALUE, value=vname)
		vl = self.character.values[vname]
		self.character.iplog.improve(vl)

	def game_session(self, fields):
		ip = int(fields['ip'])
		memo = fields['memo']
		self.character.iplog.game_session(memo, ip)

	def literal_functions(self):
		return {
			'solo' : self.character.roles.first_role,
			'rockerboy' : self.character.roles.first_role,
			'netrunner' : self.character.roles.first_role,
			'exec' : self.character.roles.first_role,
			'media' : self.character.roles.first_role,
			'lawman' : self.character.roles.first_role,
			'fixer' : self.character.roles.first_role,
			'tech' : self.character.roles.first_role,
			'medtech' : self.character.roles.first_role,
			'nomad' : self.character.roles.first_role
		}

	def slot_chip(self, fields):
		self.character.cyberware.slot_chip(fields['chip'])
		
	def swap_arms(self, fields):
		self.character.swap_arms(**fields)

	def buy(self, fields):
		itm = super().buy(fields)
		if 'therapy' in itm.get('keywords',[]):
			self.humanity_event({
				'amount': itm.humanity * 3.5, 
				'memo' : 'Recieved {}.'.format(itm.prototype['name'])
				})
		if 'paired' in itm.keywords:
			if len(itm.contained_in) > 0:
				if 'treat_as_paired' in itm.contained_in[0].keywords:
					self.character.bank.adjust_last_entry(itm.cost/2.0)

	def remove(self, fields):
		itm = CyberpunkMarket[fields['name']]
		self.character.remove_cyberware(itm)
		
	def humanity_event(self, fields):
		amt = int(fields['amount'])
		memo = fields['memo']
		self.character.humanity_record.humanity_event(amt, memo)

	def combat_number(self, fields):
		self.character.set_combat_number(int(fields['cn']))

	def character_value(self, fields):
		if not self.total_mode:
			return super().character_value(fields)
		sk = self.character.values[fields['key']]
		if not 'skill' in sk.keywords:
			return super().character_value(fields)
		fv = int(fields['value'])
		st = sk.stat
		skv = fv - st.value
		if skv < 0:
			sk.value = 0
			raise CharacterBuilderBadCommand(BADTOTAL,final=fv, stat=st.name, skill=sk.name)
		self.character.values[fields['key']].value = skv

