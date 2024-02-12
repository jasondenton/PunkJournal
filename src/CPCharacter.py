from character import BaseCharacter
from CPHumanity import HumanityRecord, NoHumanityRecord, AnimalHumanityRecord
from CPCharValues import CyberpunkCharacterValues
from CPCyberware import CyberpunkCyberbody, CyberArmContainer
from CPInventory import CyberpunkInventory
from CPGear import CyberpunkMarket
from CPfnff import FNFF
from CPRoles import CyberpunkRoleValues
from cbexception import CharacterBuilderBadCommand
from gameobj import NestableObject, PrototypedObject
from CPImprove import ImprovementLog
from ledger import BankAccount, BottomlessBankAccount
from copy import copy 

RULE_DEFAULTS = {
	'starting_cash' : 2550.00,
	'fashion_budget' : 800.00,
	'skill_points' : 86,
	'stat_points' : 62
}

NPC_DEFAULTS = {
	'starting_cash' : 255000.00,
	'fashion_budget' : 80000.00,
	'skill_points' : 999,
	'stat_points' : 99999
}

TOOL_BOOSTS = {
	'agent' : ['wardrobe and style', 'library search'],
	'medscanner' : ['first aid', 'paramedic'],
	'techscanner' : ['basic tech', 'cybertech', 'land vehicle tech', 'sea vehicle tech', 'air vehicle tech', 'electronics/security tech', 'weaponstech']
}

CYBER_BOOSTS = {
	'image enhance' : ['perception', 'lip Reading', 'conceal/reveal object'],
	'amplified hearing' : ['perception'],
	'voice stress' : ['human perception', 'interrogation'],
	'audio vox' : ['acting', 'play instrument: singing'],
	'toxin binders' : ['resist torture/drugs'],
	'cool look' : ['personal grooming'],
	'tattoo' : ['wardrobe and style'],
	'superchrome' : ['wardrobe and style']
}

CYBERWORDS = set(['cyberware', 'borgware', 'fashionware'])

FASHIONPOLICE = {
	'code' : 2034,
	'line' : 999,
	'message' : 'Killed by the Fashion Police for spending your clothing budget on toys.'
}
NOSUCHDESIGNATION = {
	'code' : 407,
	'message' : 'No such designation as {loc}.'
}
PREQNOTMET = {
	'code' : 408,
	'message' : 'Prequiesites not meet for {item}.'
}
CYBERWARE1AT = {
	'code' : 500,
	'message' : 'Buy cyberware items one at a time. Paired items are purchased together.'
}

ANIMALSONLY = {
	'code' : 235,
	'message' : 'Natural weapons and armor may only be added to animals.'
}

ONLYQUICKCN = {
	'code' : 245,
	'message' : 'Only quick characters may have a combat number.'
}

class CyberpunkCharacter(BaseCharacter):
	def _init_stage1(self):
		raise RuntimeError('Cannot create a basic Cyberpunk Character')

	def __init__(self):
		(tmp_bank, start_date) = self._init_stage1()
		self.iplog = ImprovementLog()
		self.values = CyberpunkCharacterValues(self.humanity_record)
		self.cyberware = CyberpunkCyberbody(self.humanity_record)	
		super().__init__(inventory=CyberpunkInventory(self.cyberware), bank=tmp_bank)
		self.roles = CyberpunkRoleValues(self)
		self.set_date(start_date)
		self.grease_learned = 0
		self.animal = False

	def set_date(self, date):
		super().set_date(date)
		self.iplog.date = date
		self.humanity_record.set_date(date)
		
	def fabricate_cyberarm(self): #this goes here to minimized cross dependencies
		holder = CyberArmContainer(neuroware_container=self.cyberware.designated['neuralware'], \
			humanity_record=self.humanity_record)
		holder.toggle_maxloss(False)
		arm = CyberpunkMarket['Cyberarm: right']
		mount = CyberpunkMarket['Quick Change Mount: right']
		tmp = mount.humanity
		mount.humanity = 0
		holder.install(arm)
		holder.install(mount)
		mount.humanity = tmp
		return holder

	def location_router(self, itm):
		if itm.option:
			if itm.option[0:4] == 'left':
				location = itm.option[4:].strip()
				itm.option = 'left'
			elif itm.option[0:5] == 'right':
				location = itm.option[5:].strip()
				itm.option = 'right'
			else:
				location = itm.option
			if location in self.inventory.designated:
				return location
			if 'borg' in location:
				itm.option += ' borg'
		return itm.install_in

	def special_cyberware_add(self, itm):
		if itm.isa('Subdermal Grip'):
			itm.install_in = 'neuralware'
			#self.cyberware.designated['neuralware'].toggle_maxloss(False)
			NestableObject.install(self.cyberware.designated['neuralware'], itm)
			#self.cyberware.designated['neuralware'].install(itm)
			#self.cyberware.designated['neuralware'].toggle_maxloss(True)
		if itm.isa('Grafted Muscle and Bone Lace'):
			self.values['body'].add_grafts()
		if 'linear frame' in itm.keywords:
			self.values['body'].set_linear_frame(itm.frame_level, True)
	
	def special_cyberware_removal(self, itm):
		if itm.isa('Subdermal Grip'):
			itm.install_in = 'neuralware'
			NestableObject.remove_by_example(self.cyberware.designated['neuralware'], itm)	
			#self.cyberware.designated['neuralware'].toggle_maxloss(False)
			#self.cyberware.designated['neuralware'].remove_by_example(itm)
			#self.cyberware.designated['neuralware'].toggle_maxloss(True)			
		if itm.isa('Grafted Muscle and Bone Lace'):
			self.values['body'].remove_grafts()		
		if 'linear frame' in itm.keywords:
			self.values['body'].set_linear_frame(0, True)

	def check_prereq(self, itm):
		if not 'linear frame' in itm.keywords: return
		p = True
		meta = self.cyberware.metadata()
		if itm.isa('Implanted Linear Frame Sigma'):
			p = (self.values['body'].effective >= 6 and meta['muscle grafts'] >= 1)
		if itm.isa('Implanted Linear Frame Beta'):
			p = (self.values['body'].effective >= 8 and meta['muscle grafts'] >= 2)
		if not p:
			raise CharacterBuilderBadCommand(PREQNOTMET,item=itm.name)

	def add_item(self, itm, num=1, location='carried'):
		if 'natural' in itm.keywords and not self.animal:
			raise CharacterBuilderBadCommand(ANIMALSONLY)
		if itm.isa('Spare Cyberarm'):
			itm.peg = self.fabricate_cyberarm()
		if len(itm.keywords & CYBERWORDS) == 0:
			if itm.isa('Communications Center'):
				self.add_item(CyberpunkMarket['Tracer Button'], 6)
			return super().add_item(itm,num,location)
		self.check_prereq(itm)
		#must be cyberware
		if num > 1:
			raise CharacterBuilderBadCommand(CYBERWARE1AT)
		location = self.location_router(itm)
		if location in self.inventory.designated:
			self.inventory.designated[location].install(itm)
		elif location in self.cyberware.designated:
			self.cyberware.designated[location].install(itm)
		self.special_cyberware_add(itm)

	def remove_cyberware(self, itm):
		location = self.location_router(itm)
		if location in self.inventory.designated:
			self.inventory.designated[location].remove_by_example(itm)
		elif location in self.cyberware.designated:
			self.cyberware.designated[location].remove_by_example(itm)
		self.special_cyberware_removal(itm)

	def do_gear(self):
		tools = self.inventory.inventory_view(keyword='tool', location='carried')
		tmp = [g.boost for g in tools]
		tmp += self.cybermeta['tools']
		tools_on_hand = set(tmp)
		for tool, boosted in TOOL_BOOSTS.items():
			if not tool in tools_on_hand: continue
			for skill in boosted:
				self.values[skill].tool += 1
		cyber_inst = set(self.cybermeta['cyber_enhancements'])
		for cyber, boosted in CYBER_BOOSTS.items():
			if not cyber in cyber_inst: continue
			for skill in boosted:
				self.values[skill].cyberware += 1
		bd = self.values['body']
		if bd.linear_frame == 0:
			frames = self.inventory.inventory_view(keyword='linear frame', location='carried')
			for frame in frames:
				if self.cybermeta['interface plugs'] >= frame.frame_level:
					bd.set_linear_frame(frame.frame_level, False)
					break
				else:
					self.warnings.append({
							'code' : 120,
							'line' : 0,
							'message' : 'Unable to use {} due to insufficent interface plugs.'.format(str(frame))
						})
		chairs = self.inventory.inventory_view(keyword='wheelchair', location='carried')
		if len(chairs) > 0:
			self.values['move'].has_chair = True

	def swap_arms(self, side, borg, spare_name):
		if not spare_name in self.inventory.designated:
			raise CharacterBuilderBadCommand(NOSUCHDESIGNATION, loc=spare_name)
		spare_holder = self.inventory.designated[spare_name]
		spare_arm = spare_holder.peg
		on_cost = spare_arm.check_snap() * -1
		if borg:
			parent = self.cyberware.designated['cyberarm'].borgarms
		else:
			parent = self.cyberware.designated['cyberarm'].regular
		if side.lower() == 'left':
			orig_arm = parent.left
		else:
			orig_arm = parent.right
		off_cost = orig_arm.check_snap()
		spare_arm.toggle_maxloss(True)
		orig_arm.toggle_maxloss(False)
		spare_holder.peg = orig_arm
		if side.lower() == 'left':
			parent.left = spare_arm
		else:
			parent.right = spare_arm
		self.humanity_record.adjust_max_humanity(on_cost + off_cost, 'Swapped Cyberarms')

	def chipware(self):
		for chip in self.cybermeta['chips']:
			if 'skill chip' in chip['keywords']:
				self.values[chip['option']].chip = True

	def cyberdecks(self):
		decks = self.inventory.inventory_view(keyword='cyberdeck', location='carried')
		for deck in decks:
			deck.sys_profile()
		suits = self.inventory.inventory_view(keyword='runner suit', location='carried')
		for suit in suits:
			suit.sys_profile()
			if suit.deck:
				decks.append(suit.deck)
		self.cyberdecks = decks

	def set_combat_number(self, cn):
		raise CharacterBuilderBadCommand(ONLYQUICKCN)

	def end_creation(self):
		super().end_creation()
		self.values.populate(True)
		self.iplog.initial_build(self.values)
		self.set_date('2045-01-01')

	def build_finished(self):
		super().build_finished()
		self.cybermeta = self.cyberware.metadata()
		self.do_gear()
		self.chipware()
		######### functions which calculate final dervied values, to hits, etc below this line
		self.fnff = FNFF(self)
		self.cyberdecks()

	def render(self):
		(emp, hum, mxhum) = self.humanity_record.current_humanity()
		rv = {
			'name' : self.name,
			'title' : self.title,
			'gender' : self.gender,
			'notes' : self.notes,
			'bank_ledger' : self.bank.render(),
			'bank_balance' : self.bank.balance,
			'warnings' : self.warnings,
			'humanity_record' : self.humanity_record.render(),
			'current_humanity' : hum,
			'max_humanity' : mxhum,
			'ip_log' : self.iplog.render(),
			'cyberware' : self.cyberware.render(),
			'cybermeta' : self.cyberware.metadata(),
			'cyberdecks' : [x.render() for x in self.cyberdecks],
			'token_size' : {'width' : self.token_size[0], 'height' : self.token_size[1]},
			'declared_token' : self.token,
			'declared_portrait' : self.portrait,
			'needs_cn' : False
		}
		rv.update(self.inventory.render())
		rv.update(self.fnff.render())
		rv.update(self.values.render())
		rv.update(self.roles.render())
		if not self.title:
			rv['title'] = rv['role_summary']
		return rv

class CyberpunkPCCharacter(CyberpunkCharacter):
	def _init_stage1(self):
		self.humanity_record = HumanityRecord()
		tmp_bank = BankAccount()
		start_date = '2044-12-01'
		self.creation_params = copy(RULE_DEFAULTS)
		return (tmp_bank, start_date)

	def __init__(self):
		super().__init__()
		self.bank.add_entry(self.creation_params['starting_cash'], 'Initial Deposit')
		self.bank.add_entry(self.creation_params['fashion_budget'], 'Fashion Allowance')

	def check_build(self):
		stats = 0
		for (x,v) in self.values.items():
			if 'stat' in v.keywords:
				stats += v.start
		if stats != self.creation_params['stat_points']:
			self.warnings.append({
				'code' : 204,
				'line' : 999,
				'message' : 'Character was built with {} points in stats, but has {} available to spend.'.format(stats, self.creation_params['stat_points'])
			})
		if self.values['luck'].value < 2:
			self.warnings.append({
				'code' : 206,
				'line' : 999,
				'message' : 'Players Characters must have at least 2 points in luck.'
				})
		skills = 0
		native_language = False
		for v in self.values.values():
			if 'skill' in v.keywords and v.start:
				skills += v.start
				if 'hard' in v.keywords:
					skills += v.start
				if not native_language and v.isa('language') and v.option != 'streetslang' and v.value >= 4:
					skills -= 4
					native_language = True
		skills -= self.grease_learned #start values are 1s
		if skills != self.creation_params['skill_points']:
			self.warnings.append({
				'code' : 205,
				'line' : 999,
				'message' : 'Character has built with {} points in skills, but has {} available to spend.'.format(skills, self.creation_params['skill_points'])
			})		

	def end_creation(self):
		super().end_creation()
		self.fashion_police()
		self.check_build()

	def fashion_police(self):
		clothes = self.inventory.inventory_view(keyword='fashion')
		spent = 0.0
		for itm in clothes:
			if itm.cost > 0:
				spent += itm.cost * itm.count
		spent += sum([x.cost for x in self.cyberware.designated['fashionware']])
		ticket = self.creation_params['fashion_budget'] - spent
		if ticket > 0.0:
			self.set_date('2045-12-31')
			if ticket > self.bank.balance:
				self.warnings.append(FASHIONPOLICE)
				ticket = self.bank.balance
			self.bank.add_entry(-ticket, 'Ticket from the Fashion Police.')

	def render(self):
		rv = super().render()
		rv['sheet'] = {
			'default' : 'complete',
			'logs' : True
		}
		rv['character_type'] = 'pc'
		return rv

class CyberpunkNPCCharacter(CyberpunkCharacter):
	def _init_stage1(self):
		self.humanity_record = NoHumanityRecord()
		self.iplog = ImprovementLog()
		tmp_bank = BottomlessBankAccount()
		self.creation_params = copy(RULE_DEFAULTS) # prevents breaks in exec role ability
		start_date = '2044-12-01'
		return (tmp_bank, start_date)

	def __init__(self):
		super().__init__()
		self.values.populate(False)
		for k,v in self.values.items():
			if 'stat' in v.keywords:
				v.start_max = 10
		self.roles.npc_mode = True
		self.values.npc_mode = True

	def render(self):
		rv = super().render()
		rv['sheet'] = {
			'default' : 'concise',
			'logs' : False
		}
		rv['character_type'] = 'npc'
		return rv

class CyberpunkAnimalCharacter(CyberpunkNPCCharacter):
	def _init_stage1(self):
		(tmp_bank, start_date) = super()._init_stage1()
		self.humanity_record = AnimalHumanityRecord()
		return (tmp_bank, start_date)

	def __init__(self):
		super().__init__()
		for k,v in self.values.items():
			if 'stat' in v.keywords:
				v.start_max = 999
				v.start_min = 0
				v.max = 999
				v.min = 0
			if 'skill' in v.keywords:
				v.start_min = 0
				v.min = 0
				v.default = 0
				if 'basic' in v.keywords:
					v.keywords.remove('basic')
		self.animal = True

	@staticmethod
	def prune_skills(rv):
		for k,v in rv['skills'].items():
			if v['value'] == 0 and v['stat'] in ['IN', 'TH']:
				v['show'] = False
				v['npcshow'] = False

	def render(self):
		rv = super().render()
		nap = []
		for piece in rv['armor_pieces']:
			if not 'natural' in piece['keywords']:
				nap.append(piece)
		rv['armor_pieces'] = nap 
		rv['character_type'] = 'animal'
		self.prune_skills(rv)

		return rv

class CNProxy:
	def __init__(self, real, cn):
		self.real = real 
		self.cn = cn
		self.effective = cn
		self.value = 0 

	def render(self):
		rv = self.real.render()
		rv['effective'] = self.cn 

class CyberpunkQuickValueProxy:
	def __init__(self, basev):
		self.basev = basev
		self.cn = 0

	def __getitem__(self, key):
		v = self.basev[key]
		if 'skill' in v.keywords:
			return CNProxy(self.basev[key], self.cn)
		return v 

	def populate(self, *args):
		return self.basev.populate(*args)

	def items(self):
		return self.basev.items()

	def get_used_values(self):
		qvalues = []
		take = set(['stat', 'drone'])
		for k,v in self.basev.items():
			if len(take & v.keywords) > 0:
				if v.can_set: 
					continue 
				else:
					qvalues.append(v)
		qvalues.sort(key = lambda x: x.sort)
		return [(x.abbreviation, x.value) for x in qvalues]

	def render(self):
		return {'stats' :{}, 'skills':{}}
			
class CyberpunkQuickCharacter(CyberpunkAnimalCharacter):
	def __init__(self):
		super().__init__()
		self.values = CyberpunkQuickValueProxy(self.values)
		self.values['empathy'].humanity_record = self.humanity_record 
		self.values['body'].values = 999

	def end_creation(self):
		self.non_default_values = self.values.get_used_values() 
		super().end_creation()

	def set_combat_number(self, cn):
		self.values.cn = cn 

	def render(self):
		rv = super().render()
		rv['sheet']['default'] = 'drone'
		rv['character_type'] = 'drone'
		if self.values.cn > 0:
			self.non_default_values = [('CN', self.values.cn)] + self.non_default_values
		else:
			rv['needs_cn'] = True
		rv['stats'] = self.non_default_values
		return rv



