import os 
import yaml 

from charvalues import SetOnceCharacterValue, CharacterValues
from prototype import PrototypeStore
from CPHumanity import HumanityRecord

db_path = os.environ['PUNKJOURNALDB']

ALREADYHASFRAME = {
	'code' : 2002,
	'message' : 'This character is already using a linear frame.'
}

class CyberpunkDroneValue(SetOnceCharacterValue):
	def __init__(self, proto):
		super().__init__(proto, None)

	def __getattr__(self, key):
		if key == 'effective':
			return self.value 
		else:
			return super().__getattr__(key)

class CyberpunkStat(SetOnceCharacterValue):
	#value 		-- 		the underlying score the character starts with
	#effective	--		the value to use for calculations
	#set_at		-- 		the value assigned by external modifier
	#show_as	--		string showing the on sheet value string
	@staticmethod
	def prototype_defaults():
		rv = SetOnceCharacterValue.prototype_defaults()
		rv.update({
			'start_min' : 2,
			'start_max' : 8,
			'min' : 2,
			'default' : 6,
			'setat' : None,
			'adjustment' : 0
		})
		return rv

	def __init__(self, proto):
		super().__init__(proto, None)

	def __getattr__(self, key):
		if key == 'effective':
			return self.value 
		return super().__getattr__(key)

	def __int__(self):
		return self.effective

	def render(self):
		eff = self.effective
		if self.value != eff:
			fs = '{value}/{effective}'
		else:
			fs = '{value}'
		return fs.format(value=self.value, effective=eff)

class CyberpunkPenaltyStat(CyberpunkStat):
	def __init__(self, proto):
		super().__init__(proto)
		self.penalty = 0

	def set_penalty(self, p):
		self.penalty = p

	def __getattr__(self, key):
		if key == 'effective':
			return max(self.value + self.penalty,0)
		return super().__getattr__(key)		

class CyberpunkMove(CyberpunkPenaltyStat):
	def __init__(self, proto):
		super().__init__(proto)
		self.has_chair = False

	def __getattr__(self, key):
		if key == 'effective':
			if self.has_chair:
				eff = 5 
			else:
				eff = self.value
			return max(eff + self.penalty,0)
		return super().__getattr__(key)	


class CyberpunkBody(CyberpunkStat):
	def __init__(self, proto):
		super().__init__(proto)
		self.grafts = 0
		self.linear_frame = 0
		self.implanted_frame = False
		
	def add_grafts(self):
		self.grafts += 1

	def remove_grafts(self):
		if self.grafts < 1:
			raise RuntimeError('Oops, attempt to remove a muscle graft when none are installed.')
		self.grafts -= 1

	def set_linear_frame(self, lvl, implanted=False):
		if self.linear_frame > 0 and lvl > 0:
			raise CharacterBuilderBadCommand(ALREADY_HAS_FRAME)
		self.implanted_frame = implanted
		self.linear_frame = lvl

	def calc_values(self):
		#if we are forced to check prereq (for linear frames) before a value is set,
		#force default.
		if not self.value:
			self.value = self.default 
		if self.grafts > 0:
			work = min(self.value + self.grafts * 2, 10)
		else:
			work = self.value #bypass for animals
		show = work
		if self.linear_frame > 0:
			frame = 10 + self.linear_frame * 2
			if self.implanted_frame:
				work = frame
				show = frame
			else:
				show = frame
		return (work,show)

	def __getattr__(self, key):
		if key == 'effective':
			(wrk,shw) = self.calc_values()
			return wrk 	
		return super().__getattr__(key)	

	def unarmed_damage(self):
		eff = self.effective 
		if eff >= 11:
			return 4 
		if eff >= 7:
			return 3
		if eff >= 5:
			return 2
		return 1

	def render(self):
		(wrk, shw) = self.calc_values()
		if wrk == shw:
			return str(wrk)
		else:
			return '{}/{}'.format(wrk,shw)

class CyberpunkEmpathy(CyberpunkStat):
	def __setattr__(self, key, value):
		rv = super().__setattr__(key, value)
		if key == 'value':
			self.humanity_record.starting_empathy(int(value))
			self.original = value
		return rv

	def __getattr__(self, key):
		if key == 'effective':
			(eff, t1, t2) = self.humanity_record.current_humanity()
			return eff
		return super().__getattr__(key)

	def render(self):
		return str(self.effective)

class CyberpunkSkill(SetOnceCharacterValue):
	@staticmethod
	def prototype_defaults():
		rv = SetOnceCharacterValue.prototype_defaults()
		rv.update({
			'stat' : None,
			'start_min' : 0,
			'start_max' : 6,
			'min' : 0,
			'max' : 10,
			'default' : 0,
			'chip' : False,
			'tool' : 0,
			'cyberware' : False,
			'role_boost' : [],
			'notes' : []
		})
		return rv

	@staticmethod 
	def prototype_contract():
		rv = SetOnceCharacterValue.prototype_contract()
		rv.update({
			'stat' : str,
			'chip' : bool,
			'tool' : int,
			'cyberware' : int,
			'notes' : list
		})
		return rv

	def __int__(self):
		return self.value 

	def _calc_effective(self):
		stat = self.stat.effective
		if self.value == None:
			self.value = 0
		skpart = self.value
		if self.chip and self.value < 3:
			skpart = 3
		effective = skpart + stat 
		effective += (self.tool + self.cyberware) * 2
		for rb in self.role_boost:
			effective += rb.value
		return effective

	def __getattr__(self, key):
		if key == 'effective':
			return self._calc_effective()
		return super().__getattr__(key)

	def show_value(self):
		if self.chip and self.value < 3:
			return 3
		return self.value

	def render(self):
		hat = 0
		for b in self.role_boost:
			if b.value > 0:
				hat += 1
		sbase = hat or self.tool or self.cyberware or self.chip or self.value > self.default 
		show = sbase or self.value > 0
		#npc_show = sbase or 'in_combat_block' in self.keywords
		npc_show = not 'in_combat_block' in self.keywords and show
		rv = super().render()
		eff = self._calc_effective()
		rv['notes'] = self.notes
		rv['stat'] = self.stat.abbreviation
		rv['effective'] = eff
		rv['show'] = show
		rv['npcshow'] = npc_show
		rv['chip'] = self.chip > 0
		rv['tool'] = self.tool > 0
		rv['cyberware'] = self.cyberware
		rv['role_boost'] = hat
		rv['value'] = self.show_value()
		return rv

def cp_char_value_factory(proto, opt):
	if proto['name'] == 'Body' :
		return CyberpunkBody(proto)
	elif proto['name'] == 'Move':
		return CyberpunkMove(proto)
	elif proto['name'] in ['Reflexes', 'Dexterity']:
		return CyberpunkPenaltyStat(proto)
	elif proto['name'] == 'Empathy':
		return CyberpunkEmpathy(proto)
	elif 'stat' in proto['keywords']:
		return CyberpunkStat(proto)
	elif 'skill' in proto['keywords']:
		return CyberpunkSkill(proto, opt)
	else:
		raise RuntimeError('Invalid character value {}.'.format(proto['name']))

class CyberpunkCharacterValueDatabase(PrototypeStore):
	def __init__(self):
		super().__init__(self.cp_char_value_factory)
		with open(os.path.join(db_path,'character_values.yaml')) as fin:
			data = yaml.safe_load(fin)
		stats = []
		skills = []
		dronev = []
		for itm in data:
			if 'stat' in itm['keywords']:
				stats.append(itm)
			elif 'skill' in itm['keywords']:
				skills.append(itm)
			elif 'drone' in itm['keywords']:
				dronev.append(itm)
		self.add(stats, CyberpunkStat.prototype_defaults(), CyberpunkStat.prototype_contract())
		self.add(skills, CyberpunkSkill.prototype_defaults(), CyberpunkSkill.prototype_contract())
		self.add(dronev, CyberpunkDroneValue.prototype_defaults(), CyberpunkDroneValue.prototype_contract())

	def cp_char_value_factory(self, proto, opt):
		if proto['name'] == 'Body' :
			return CyberpunkBody(proto)
		elif proto['name'] == 'Move':
			return CyberpunkMove(proto)
		elif proto['name'] in ['Reflexes', 'Dexterity']:
			return CyberpunkPenaltyStat(proto)
		elif proto['name'] == 'Empathy':
			return CyberpunkEmpathy(proto)
		elif 'stat' in proto['keywords']:
			return CyberpunkStat(proto)
		elif 'skill' in proto['keywords']:
			return CyberpunkSkill(proto, opt)
		elif 'drone' in proto['keywords']:
			return CyberpunkDroneValue(proto)
		else:
			raise RuntimeError('Invalid character value {}.'.format(proto['name']))

CPValuesDB = CyberpunkCharacterValueDatabase()

class CyberpunkCharacterValues(CharacterValues):
	def __init__(self, humrec):
		super().__init__(CPValuesDB)
		self['empathy'].humanity_record = humrec 
		self.npc_mode = False
		self['language: streetslang'].default = 2
		
	def __getitem__(self, key):
		v = super().__getitem__(key)
		if 'skill' in v.keywords:
			if self.npc_mode:
				v.start_max = 10
			if isinstance(v.stat,str):
				st = super().__getitem__(v.stat)
				v.stat = st 
		return v

	def get_stats_skills(self):
		rv = {
			'stats' : {},
			'skills' : {}
		}
		for k,v in self.data.items():
			if 'stat' in v.keywords:
				rv['stats'][k] = v
			elif 'skill' in v.keywords:
				rv['skills'][k] = v
		return rv

	def render(self):
		sts = self.get_stats_skills()
		ns = {}
		for k,d in sts.items():
			ns[k] = {}
			names = sorted(list(d.keys()))
			for name in names:
				n = d[name].name
				tmp = d[name].render()
				ns[k][n] = tmp
		return ns




