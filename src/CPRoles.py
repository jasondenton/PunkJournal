import os 
import yaml 

from aliasdict import CaseIgnoreAliasDict
from cbexception import CharacterBuilderBadCommand
from prototype import PrototypeStore
from charvalues import CharacterValues, SetOnceCharacterValue, SummedValue, SETONCE
from CPCharValues import CyberpunkSkill
from CPGear import CyberpunkMarket

db_path = os.environ['PUNKJOURNALDB']

ROLEMUSTRAISE = {
	'code' : 1034,
	'message' : 'Role abilities can only be advanced by selecting a role at character creation, or raised with IP later.'
}

NOMULTICLASS = {
	'code' : 1035,
	'message' : 'Before you start a new role you must reach level 4 in your previous role(s).'
}

LANGNOTAVAIL = {
	'code' : 1046,
	'message' : 'You have learned every free lanaguage you can at your current level of operator.'
}

LANGALREADY = {
	'code' : 1056,
	'message' : 'Language already known.'
}

MUSTRAISEPARENT = {
	'code' : 2356,
	'message' : 'You must raise your {parent} skill before you may improve {sub}.'
}

ALREADYKNOWN = {
	'code' : 2351,
	'message' : 'Forumla for {recipie} already known.'
}

NOSUCHRECIPIE = {
	'code' : 2251,
	'message' : 'No such formula as {recipie}.'
}

MUSTPHARMA = {
	'code' : 234,
	'message' : 'You must increase your Pharmaceuticals ability before learning another formula.'
}

NOMOTO = {
	'code' : 1122,
	'message' : 'You can not use Moto to get a {item}.'
}

MOTOUSED = {
	'code': 1234,
	'message' : 'You have used your allotment of vehicles/upgrades.'
}

INSUFMOTO = {
	'code' : 1352,
	'message' : 'You need moto level {mlvl} to get a {item}.'
}


class CyberpunkRoleAbility(SetOnceCharacterValue):
	@staticmethod
	def prototype_defaults():
		rv = SetOnceCharacterValue.prototype_defaults()
		rv.update({
			'start_min' : 0,
			'start_max' : 4,
			'min' : 0,
			'max' : 10,
			'value' : None,
			'default' : 0,
			'start' : 0,
			'role' : None,
			'keywords' : set(['role ability']),
			'text' : '',
			'option' : False,
			'parent' : None
		})
		return rv

	def __init__(self, proto):
		super().__init__(proto,None)
		self.manager = None

	def __setattr__(self, key, vl):
		if key == 'value': 
			if self.manager == None or not self.manager.npc_mode:
				if vl != 0:
					raise CharacterBuilderBadCommand(ROLEMUSTRAISE)
			else: #npc_mode
				if vl != 0:
					if self.value != 0:
						raise CharacterBuilderBadCommand(SETONCE,value=self.name)
					for i in range(vl):
						self.increment()
					return vl
		return super().__setattr__(key, vl)

	def __int__(self):
		return self.value 
		
	def increment(self):
		cv = self.value 
		if cv == 0 and 'role sub' not in self.keywords:
			if not self.manager.can_multiclass:
				raise CharacterBuilderBadCommand(NOMULTICLASS)
			self.manager.can_multiclass = False
		if cv == 3:
			self.manager.can_multiclass = True
		super().increment()

	def render(self):
		return {
			'role': self.role,
			'name' : self.name,
			'value' : self.value,
			'text' : self.text 
		}

class TieredAbility(CyberpunkRoleAbility):
	def get_tier(self):
		return self.tier_map[self.value]

	def increment(self):
		super().increment()
		self.set_tier_data()

class TierMappedAbility(TieredAbility):
	def set_tier_data(self):
		tier = self.tiers[self.get_tier()]
		for (k,v) in tier.items():
			self.__setattr__(k,v)
		return tier 

	def increment(self):
		super().increment()
		self.set_tier_data()

	def render(self):
		tdat = self.set_tier_data()
		rv = super().render()
		rv.update(tdat)
		return rv

class BackupAbility(TieredAbility):
	def set_tier_data(self):
		pass 
		
	def render(self):
		t = self.get_tier()
		helpers = [self.tiers[t]]
		if self.value < 10:
			helpers += [self.tiers[t+1]]
		rv = super().render()
		rv['helpers'] = helpers
		return rv

class TeamworkAbility(TierMappedAbility):
	def __init__(self, proto):
		super().__init__(proto)

	def increment(self):
		super().increment()
		if self.value == 1:
			self.manager.add_item('businesswear top', location='worn')
			self.manager.add_item('businesswear bottoms', location='worn')
			self.manager.add_item('businesswear footwear', location='worn')
			self.manager.add_item('businesswear jacket', location='worn')
			self.manager.character.creation_params['fashion_budget'] +=  1550

class OperatorAbility(TierMappedAbility):

	def __init__(self, proto):
		super().__init__(proto)
		self.lang_avail = 0

	def increment(self):
		super().increment()
		if self.value == 3:
			self.lang_avail += 1
		elif self.value == 5:
			self.lang_avail += 2
		elif self.value == 7:
			self.lang_avail += 3

	def grease_language(self, lang):
		if self.lang_avail < 1:
			raise CharacterBuilderBadCommand(LANGNOTAVAIL)
		ln = self.manager.character.values['language: %s' % lang]
		if ln.value and ln.value > 0:
			raise CharacterBuilderBadCommand(LANGALREADY)
		ln.increment()
		ln.increment()
		ln.increment()
		ln.increment()
		self.manager.character.grease_learned += 1
		self.lang_avail -= 1
		self.manager.character.grease_first = True

	def set_tier_data(self):
		tier_dat = super().set_tier_data()
		tier = self.get_tier()
		self.discount = 10
		self.haggle = self.haggle_tiers[0:tier]
		self.nightmarket = ''
		if tier >= 3:
			self.nightmarket = self.nightmarket_tiers[0]
		if tier >= 5:
			self.nightmarket += self.nightmarket_tiers[1]
			self.discount = 20
			self.haggle.remove('REMOVE')
			self.haggle[0].replace('10','20')
		tier_dat.update({
			'haggle' : self.haggle,
			'nightmarket' : self.nightmarket,
			'discount' : self.discount
		})
		return tier_dat

class RoleParentAbility(CyberpunkRoleAbility):
	def __init__(self, proto):
		super().__init__(proto)
		self.available_boosts = 0
		self.subs = []

	def add_sub(self, sub):
		self.subs.append(sub)

	def render(self):
		rv = super().render()
		self.subs.sort(key=lambda x: x.name)
		rv['subs'] = []
		for sub in self.subs:
			rv['subs'].append(sub.render())
		return rv

class RoleSubAbility(CyberpunkRoleAbility):
	def increment(self):
		if self.parent.available_boosts < 1:
			raise CharacterBuilderBadCommand(MUSTRAISEPARENT, parent=self.parent.name, sub=self.name)
		self.parent.available_boosts -= 1
		super().increment()

class MakerRoleAbility(RoleParentAbility):
	def increment(self):
		super().increment()
		self.available_boosts += 2

class MedicineRoleAbility(RoleParentAbility):
	def increment(self):
		super().increment()
		self.available_boosts += 1	

class SurgeryAbility(RoleSubAbility):
	def increment(self):
		super().increment()
		CyberpunkRoleAbility.increment(self)

class PharmaAbility(RoleSubAbility):
	def __init__(self, proto):
		super().__init__(proto)
		self.known_recipies = []
		self.avail = 0

	def increment(self):
		super().increment()
		self.avail += 1

	def learn(self, rc):
		rc = rc.lower()
		if rc in self.known_recipies:
			raise CharacterBuilderBadCommand(ALREADYKNOWN,recipie=rc)
		if rc not in self.recipies.keys():
			raise CharacterBuilderBadCommand(NOSUCHRECIPIE, recipie=rc)
		if self.avail < 1:
			raise CharacterBuilderBadCommand(MUSTPHARMA)
		self.known_recipies.append(rc)
		self.avail -= 1

	def render(self):
		rv = super().render()
		rv['known_recipies'] = self.known_recipies
		rv['recipies'] = self.recipies
		return rv

class CryotechAbility(RoleSubAbility):
	def set_charges(self, ch):
		p = self.manager.character.inventory.designated.get('__mt_cryopump', False)
		if p != False: p.charges = ch 

	def increment(self):
		super().increment()
		if self.value == 1:
			self.manager.add_item('Cryopump')
			self.manager.character.inventory.designate('Cryopump', '__mt_cryopump')
		if self.value == 2:
			self.manager.add_item('Cryotank',1,'Cryolab')
		if self.value == 3:
			self.manager.add_item('Cryotank',1,'Home')
		if self.value == 4:
			self.manager.add_item('Cryotank',2,'Home')
			self.set_charges(2)
		if self.value == 5:
			self.manager.add_item('Cryotank',3,'Home')
			self.set_charges(3)


@SummedValue
class ProxySkill(CyberpunkSkill):
	pass

def role_ability_factory(proto, opt):
	name = proto['name']
	simple_tiered = ['Interface', 'Charismatic Impact', 'Credibility']
	if name in simple_tiered:
		return TierMappedAbility(proto)
	if name == 'Teamwork':
		return TeamworkAbility(proto)
	if name == 'Backup':
		return BackupAbility(proto)
	if name == 'Operator':
		return OperatorAbility(proto)
	if name == 'Maker' :
		return MakerRoleAbility(proto)
	if name == 'Medicine' :
		return MedicineRoleAbility(proto)
	if name == 'Surgery' :
		return SurgeryAbility(proto)
	if name == 'Cryosystems Operation':
		return CryotechAbility(proto)
	if name == 'Pharmaceuticals':
		return PharmaAbility(proto)
	if name == 'Medical Tech':
		return ProxySkill(proto, None)
	if name == 'Surgery_proxy_XX':
		return ProxySkill(proto, None)
	if name == 'Moto':
		return MotoAbility(proto)
	if 'role sub' in proto['keywords']:
		return RoleSubAbility(proto)
	return CyberpunkRoleAbility(proto)

class MotoAbility(CyberpunkRoleAbility):
	def __init__(self, proto):
		super().__init__(proto)
		self.available = 0
		self.biggun = 0 #0 not elig, 1 elig, 2 taken
		self.permission = self.permission_values[0]

	def increment(self):
		super().increment()
		self.available += 1
		if self.value == 10:
			self.permission = self.permission_values[1]

	def big_gun(self, itm):               
		if itm.prototype['name'] in ['Rhinemetall EMG-86 Railgun', 
			'Tsunami Arms Helix', 'Militech "Cowboy" U-56 Grenade Launcher']:
			return True
		return False

	def moto(self, itm):
		if self.big_gun(itm):
			if self.biggun == 1:
				self.biggun += 1
				itm.moto = 1
		else:
			if self.available < 1:
				raise CharacterBuilderBadCommand(MOTOUSED)
		if itm.name == 'Vehicle Heavy Weapon Mount':
			self.biggun += 1
		imoto = itm.get('moto', -1)
		if imoto == -1:
			raise CharacterBuilderBadCommand(NOMOTO,item=itm)
		if self.value < imoto:
			raise CharacterBuilderBadCommand(INSUFMOTO,mlvl=imoto,item=itm)
		self.manager.add_item(itm,1,location=None)
		self.available -= 1

	def render(self):
		rv = super().render()
		rv['permission'] = self.permission
		return rv

class RoleDatabase(PrototypeStore):
	def __init__(self):
		super().__init__(role_ability_factory)
		with open(os.path.join(db_path,'role_abilities.yaml')) as fin:
			data = yaml.safe_load(fin)
		with open(os.path.join(db_path,'role_text.yaml')) as fin:
			tdata = yaml.safe_load(fin)
		for ab in data:
			if ab['name'] in tdata:
				ab.update(tdata[ab['name']])
			if 'tier_map' in ab:
				tmp = ab['tier_map'].split(',')
				ab['tier_map'] = [0] + [int(x) for x in tmp]
			if 'tiers' in ab:
				ab['tiers'] = [{}] + ab['tiers']
		self.add(data, CyberpunkRoleAbility.prototype_defaults(), CyberpunkRoleAbility.prototype_contract())

RoleAbilityDB = RoleDatabase()

class CyberpunkRoleValues(CharacterValues):
	def __init__(self, chr):
		super().__init__(RoleAbilityDB)
		self.populate()
		self.character = chr
		self.rolemap = CaseIgnoreAliasDict()
		for (k,v) in self.data.items():
			v.manager = self
			if 'role ability' in v.keywords:
				self.rolemap[v.role] = v
			for bst in v.get('improves',[]):
				bsk = self.character.values[bst]
				bsk.role_boost.append(v)
			if v.parent:
				v.parent = self[v.parent]
				v.parent.add_sub(v)
			if v.isa('Medical Tech'):
				v.add_part(self['Cryosystems Operation'])
				v.add_part(self['Pharmaceuticals'])
			if v.isa('Surgery_proxy_XX'):
				v.add_part(self['Surgery'])
		for k,v in self.data.items():
			self.character.values[k] = v 
		self.can_multiclass = True
		self.npc_mode = False

	def add_item(self, itmname, number=1, location='carried'):
		if isinstance(itmname,str):
			itm = CyberpunkMarket[itmname]
		else:
			itm = itmname
		self.character.add_item(itm, number, location)
	
	def render(self):
		rv = []
		for (k,v) in self.rolemap.items():
			if v.value > 0:
				rv.append(v.render())
		rv.sort(key=lambda x: -x['value'])
		rls = [x['role'] for x in rv]
		summary = ' / '.join(rls)
		rv = {
			'role_summary' : summary,
			'roles' : rv
		}
		return rv

	def first_role(self, role):
		ab = self.rolemap[role]
		ab.increment()
		ab.increment()
		ab.increment()
		ab.increment()