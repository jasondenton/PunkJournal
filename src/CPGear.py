import yaml
from copy import copy
import os 
from gameobj import PhysicalObject, NOTENOUGHSLOTS
from prototype import PrototypeStore
from cbexception import CharacterBuilderBadCommand 
from CPVehicles import Vehicle, VehicleUpgrade, vehicle_factory, vehicle_upgrade_factory
from CPBaseObj import NonUpgradeableObject, UpgradeableObject
from containers import ContainerPair

db_path = os.environ['PUNKJOURNALDB']

HASSCOPE = {
	'code' : 3001,
	'message' : 'This gun already has a scope.'
}
HASMAGAZINE = {
	'code' : 3002,
	'message' : 'This gun already has an upgraded magazine.'
}
HASBARREL = {
	'code' : 3003,
	'message' : 'This gun already has an under barrel attachment.'
}
NOMODSINEXOTICS = {
	'code' : 3004,
	'message' : 'Weapon attachments may not be installed in exotic weapons.'
}
HASSMARTLINK = {
	'code' : 3005,
	'message' : 'Weapon already has a smartlink.'
}
NOTCOMPATIBLE = {
	'code' : 115,
	'message' : 'Cannot install {attachment} in {item}.'
}

ALREADYINSTALLED = {
	'code' : 3007,
	'message' : 'There is already a cyberdeck installed in this Bodyweight Suit.'
}

AMMO_NAMES = {
	'medium pistol' : '9mm bullets',
	'heavy pistol' : '11mm bullets',
	'very heavy pistol' : '12mm bullets',
	'rifle' : '7.62 bullets',
	'shotgun' : 'Shotgun Shells',
	'grenade' : 'Grenades',
	'rocket' : 'Rockets',
	'paint' : 'Paint Balls',
	'battery' : 'Batter Packs',
	'flamer' : 'Flamethrower Fuel',
	'bolts' : 'Bolts',
	'arrows' : 'Arrows',
	'darts' : 'Darts',
	'flechette' : 'Flechettes'
}

GUNNOTES = {
	'sp11' : 'Ignores SP11 or less.',
	'reload 2' : '2 actions to reload.',
	'bod11' : 'Body 11+ to fire.',
	'noablate' : 'Does not ablate armor.',
	'stun' : 'Does not cause critical injuries and does not reduce HP below 1.',
	'nocrit' : 'Does not cause critical injuries.',
	'noaimed' : 'No aimed shots.',
	'onlyauto' : 'May only be fired on autofire.',
	'driver fire' : 'Driver may use an action to fire this weapon.'
}

MAGSIZE = {
	'Medium Pistol' : [12,18,36],
	'Heavy Pistol' : [8,14,28],
	'Very Heavy Pistol' : [8,14,28],
	'Submachine Gun' : [30,40,50],
	'Heavy Submachine Gun' : [40,50,60],
	'Shotgun' : [4,8,16],
	'Assault Rifle' : [25, 35, 45],
	'Sniper Rifle' : [4,8,12],
	'Grenade Launcher' : [2,4,6],
	'Rocket Launcher' : [1,2,4],
	'Grenade Launcher Underbarrel' : [1,1,1],
}

class CyberpunkAmmo(NonUpgradeableObject):
	@staticmethod
	def prototype_defaults():
		rv = PhysicalObject.prototype_defaults()
		rv.update({
			'count' : 10
		})
		return rv

	@staticmethod
	def prototype_contract():
		rv = PhysicalObject.prototype_contract()
		rv.update({
			'ammo_class' : str,
			'count' : int
		})
		return rv

	def render(self):
		rv = super().render()
		rv['ammo_class'] = self.ammo_class
		return rv

class CyberpunkWeapon(UpgradeableObject):
	@staticmethod
	def prototype_defaults():
		rv = PhysicalObject.prototype_defaults()
		rv.update({
			'quality': 'standard',
			'wkind' : 'Unknown',
			'allowed_upgrades' : ['conceal', 'slots', 'quality', 'complexity'],
			'pass_notes' : False
		})
		return rv

	@staticmethod
	def prototype_contract():
		rv = PhysicalObject.prototype_contract()
		rv.update({
			'rof' : int,
			'hands' : int,
			'skill' : str,
			'concealable' : bool,
			'damage_dice' : int,
			'quality' : str
		})
		return rv

	def __getattr__(self, key):
		if key == 'accuracy':
			if self.get('quality','standard') == 'excellent':
				return 1 
			else:
				return 0 
		return super().__getattr__(key)

	def render(self):
		rv = super().render()
		rv.update({
			'kind' : 'weapon',
			'rof' : self.rof,
			'damage' : '{}d6'.format(self.damage_dice),
			'skill' : self.skill,
			'accuracy' : self.accuracy,
			'concealable' : self.concealable,
			'hands' : self.hands,
			'tohit' : self.get('tohit', 0),  #set in CPfnff
			'wkind' : self.wkind,
			'armor_pierce' : False
		})
		return rv

class CyberpunkMeleeWeapon(CyberpunkWeapon):
	def render(self):
		rv = super().render()
		if self.quality == 'poor':
			rv['notes'].insert(0, 'Breaks on a 1.')
		rv.update({
			'subkind' :'melee'
		})
		if not 'nerf' in self.keywords:
			rv['armor_pierce'] = True
		return rv

class CyberpunkGun(CyberpunkWeapon):
	@staticmethod
	def prototype_defaults():
		rv = CyberpunkWeapon.prototype_defaults()
		rv.update({
			'has_smartlink' : False,
			'max_container_size' : 3,
			'has_scope' : False,
			'has_barrel' : False,
			'has_smartlink' : False,
			'magkind' : 0
		})
		return rv

	#@staticmethod
	def prototype_contract():
		rv = CyberpunkWeapon.prototype_contract()
		rv.update({
			'ammo_class' : str
		})
		return rv

	def __init__(self, proto, opt):
		super().__init__(proto, opt)
		self.weapons = []
		self.mag_kind = 0
		if opt != None:
			self.name = opt 
			self.disply_name = opt 

	def _check_install(self, mod):
		if 'exotic' in self.keywords:
			return CharacterBuilderBadCommand(NOMODSINEXOTICS)
		if 'scope' in self.keywords and self.has_scope:
			return CharacterBuilderBadCommand(HASSCOPE)
		elif 'magazine' in self.keywords and self.magkind > 0:
			return CharacterBuilderBadCommand(HASMAGAZINE)
		elif 'underbarrel' in self.keywords and self.has_barrel:
			return CharacterBuilderBadCommand(HASBARREL)
		elif mod.isa('Smartgun Link') and self.has_smartlink:
			return CharacterBuilderBadCommand(HASSMARTLINK)
		return super()._check_install(mod)

	def install(self, mod):
		super().install(mod)
		if 'magazine' in mod.keywords:
			self.mag_kind = mod.mag_kind
			self.has_magazine = True
			self.conceal = False
		if 'underbarrel' in mod.keywords:
			self.has_barrel = True
		if 'weapon' in mod.keywords:
			self.weapons.append(mod)
			mod.is_attached = True
		if 'scope' in mod.keywords:
			self.has_scope = True
		if mod.isa('Smartgun Link'):
			self.has_smartlink = True
		if 'concealable' in mod and not mod.concealable: 
			self.conceal = False

	def magsize(self):
		mg = self.get('magazine', -1)
		mc = self.get('mag_class', None)
		kd = self.get('mag_kind', 0)

		if kd > 0 or mg < 0:
			sz = MAGSIZE[self.mag_class][self.mag_kind]
		else:
			sz = mg 
		return sz

	def render(self):
		rv = super().render()
		if self.get('quality','standard') == 'poor':
			rv['notes'].insert(0, 'Jams on a 1.')
		for k,v in GUNNOTES.items():
			if k in self.keywords:
				rv['notes'].append(v)
		sweaps = []
		ropts = []
		for opt in rv['contents']:
			ropts.append(opt['name'])
			if 'weapon' in opt['keywords']:
				sweaps.append(opt)
		attachments = ', '.join(ropts)
		rv.update({
			'subkind' : 'gun',
			'magazine_size' : self.magsize(),
			'ammo_type' : self.ammo_class,
			'autofire' : self.get('autofire', 0),
			'concealable' : self.concealable,
			'ammo_name' : AMMO_NAMES[self.ammo_class],
			'sub_weapons' : sweaps,
			'attachments' : attachments,
			'smartlink' : self.get('has_smartlink', False),
			'auto_tohit' : self.get('auto_tohit',0),
			'is_attached' : self.get('is_attached', False)
		})
		return rv

class CyberpunkArmor(UpgradeableObject):
	@staticmethod
	def prototype_defaults():
		rv = PhysicalObject.prototype_defaults()
		rv.update({
			'penalty' : 0,
			'allowed_upgrades' : ['armor', 'complexity']
		})
		return rv

	@staticmethod
	def prototype_contract():
		rv = PhysicalObject.prototype_contract()
		rv.update({
			'sp' : int,
			'penalty' : int
		})
		return rv

	def render(self):
		rv = super().render()
		rv['sp'] = self.sp 
		rv['penalty'] = self.penalty
		return rv

class Cyberware(UpgradeableObject):
	@staticmethod
	def prototype_defaults():
		rv = PhysicalObject.prototype_defaults()
		rv.update({
			'weight' : 0,
			'enables' : False,
			'humanity' : 0,
			'allowed_upgrades' : ['humanity', 'complexity'],
		})
		return rv

	@staticmethod
	def prototype_contract():
		rv = PhysicalObject.prototype_contract()
		rv.update({
			'enables' : bool
		})
		return rv

	def render(self):
		rv = super().render()
		oname = self.get('display_name', self.name)
		fn = self.get('full_name', oname)
		rv['full_name'] = fn.format(**self.__dict__).capitalize()
		return rv

class PopupWeaponHolder(Cyberware):
	def __init__(self, proto, option):
		super().__init__(proto, option)

	def install(self, itm):
		itm.concealable = True
		super().install(itm)

class PopupMeleeWeapon(PopupWeaponHolder):
	def _check_install(self, itm):
		if itm.isa('Light Melee Weapon') or \
			itm.isa('Medium Melee Weapon') or \
			itm.isa('Heavy Melee Weapon'): return False
		return CharacterBuilderBadCommand(NOTCOMPATIBLE, attachment=itm, item=self.name)

class PopupRangedWeapon(PopupWeaponHolder):
	def _check_install(self, itm):
		if 'ranged' in itm.keywords and \
			'weapon' in itm.keywords and \
			itm.get('hands', 1) == 1: return False
		return CharacterBuilderBadCommand(NOTCOMPATIBLE, attachment=itm, item=self.name)

class SmartlinkOnly(CyberpunkGun):
	def _check_install(self, itm):
		if itm.isa('Smartgun Link'): return False
		return CharacterBuilderBadCommand(NOTCOMPATIBLE, attachment=itm, item=self.name)

	def install(self, itm):
		super().install(itm)

class CyberarmCyberdeck(Cyberware):
	def __init__(self, proto, option):
		super().__init__(proto, option)
		self.has_deck = False 

	def _check_install(self, itm):
		if 'cyberdeck' in itm.keywords and not self.has_deck: return False
		return CharacterBuilderBadCommand(NOTCOMPATIBLE, attachment=itm, item=self.name)

	def install(self, itm):
		super().install(itm)
		itm.max_container_size += 1
		self.has_deck = True

	def render(self):
		rv = super().render()
		rv['notes'] = []
		return rv

class SwapableArm(NonUpgradeableObject):
	def install(self,itm):
		self.peg.install(itm)

	def remove_by_example(self,itm):
		self.peg.remove_by_example(itm)
		
	def render(self):
		rv = super().render()
		arm = self.peg.render()
		rv['contents'] = arm[1:]
		return rv 

class CyberpunkSoftware(NonUpgradeableObject):
	@staticmethod
	def prototype_defaults():
		rv = PhysicalObject.prototype_defaults()
		rv.update({
			'weight' : 0,
			'rez' : 0,
			'perception' : 0,
			'attack' : 0,
			'defense' : 0,
			'speed' : 0,
			'ice' : False,
			'icon' : 'Icon description missing',
			'install_in' : 'cyberdeck'
		})
		return rv

	@staticmethod
	def prototype_contract():
		rv = PhysicalObject.prototype_contract()
		rv.update({
			'rez' : int,
			'rez' : int,
			'perception' : int,
			'attack' : int,
			'defense' : int,
			'speed' : int
		})
		return rv

	def __init__(self, proto, option):
		super().__init__(proto,option)
		if 'defender' in self.keywords:
			self.subkind = 'Defender'
		elif 'attacker' in self.keywords:
			self.subkind = 'Attacker'
		elif 'booster' in self.keywords:
			self.subkind = 'Booster'
		elif 'black ice' in self.keywords:
			self.subkind = 'Black ICE'
			self.ice = True
		elif 'demon' in self.keywords:
			self.subkind = 'Demon'
			self.ice = True 
		elif 'homebrew' in self.keywords:
			self.subkind = 'Homebrew'
		else:
			self.subkind = 'Unknown'
		if 'anti-program' in self.keywords:
			self.subkind = 'Anti-program ' + self.subkind
		if 'anti-personal' in self.keywords:
			self.subkind = 'Anti-Personal ' + self.subkind 

	def render(self):
		rv = super().render()
		rv.update({
			'kind' : 'software',
			'subkind' : self.subkind,
			'icon' : self.icon,
			'rez' : self.rez,
			'attack' : self.attack,
			'defense' : self.defense,
			'speed' : self.speed,
			'perception' : self.perception
		})
		return rv

class Cyberdeck(UpgradeableObject):
	def __init__(self, proto, option):
		super().__init__(proto,option)
		self.runner_suit = None 
		self.allowed_upgrades = ['slots', 'complexity']

	def sys_profile(self, extra=[]):
		everything = self.contents + extra
		self.hardware = []
		self.software = []
		for c in everything:
			if 'hardware' in c.keywords:
				self.hardware.append(c)
			elif 'software' in c.keywords:
				self.software.append(c)			
		self.available = self.max_container_size - self.used_slots

	def render(self):
		#assume sys_profile has already happened
		rv = super().render()
		rv.update({
			'hardware' : [x.render() for x in self.hardware],
			'software' : [x.render() for x in self.software],
			'available' : self.available,
			'ability' : self.get('ability',None),
			'notes' : [],
			'contents' : []
		})
		if len(self.hardware) > 0:
			rv['contents'].append({'name': '{} hardware mods'.format(len(self.hardware)), 'contents' : []})
		if len(self.software) > 0:
			rv['contents'].append({'name': '{} programs'.format(len(self.software)), 'contents' : []})
		return rv

class CyberdeckSplitSlots(Cyberdeck):
	def _check_install(self, itm):
		if 'software' in itm.keywords:
			if itm.needs_slots > self.available_software_slots():
				return CharacterBuilderBadCommand(NOTENOUGHSLOTS, attachment=itm, item=self.name)
		if 'hardware' in itm.keywords:
			if itm.needs_slots > self.available_hardware_slots():
				return CharacterBuilderBadCommand(NOTENOUGHSLOTS, attachment=itm, item=self.name)
		return False

	def available_software_slots(self):
		inst = 0
		for itm in self.contents:
			if 'software' in itm.keywords:
				inst += itm.needs_slots 
		return self.software_slots - inst 

	def available_hardware_slots(self):
		inst = 0
		for itm in self.contents:
			if 'software' in itm.keywords:
				softinst += itm.needs_slots 
		return self.hardware_slots - inst

class BodyweightSuit(CyberpunkArmor):
	def __init__(self, proto, option):
		super().__init__(proto, option)
		self.can_accept = set(['cyberdeck', 'hardware'])
		self.deck = False
		self.allowed_upgrades = ['armor', 'slots']

	def _check_install(self, itm):
		if len(itm.keywords & self.can_accept) == 0:
			return CharacterBuilderBadCommand(NOTCOMPATIBLE, attachment=str(itm), item=str(self))
		#if itm.needs_slots > 1:
		#	return CharacterBuilderBadCommand(NOTCOMPATIBLE, attachment=str(itm), item=str(self))
		if 'cyberdeck' in itm.keywords and self.deck:
				return CharacterBuilderBadCommand(ALREADYINSTALLED)
		return False

	def sys_profile(self):
		if not self.deck: return
		self.deck.sys_profile(self.contents)

	def install(self, itm):
		if 'cyberdeck' in itm.keywords:
			self.deck = itm
		else:
			super().install(itm)

	def render(self):
		rv = super().render()
		if self.deck:
			deck = self.deck.render()
			rv['contents'] = [deck]
			rv['cyberdeck'] = deck
		return rv

class CyberpunkSmartGlasses(UpgradeableObject):
	def _check_install(self, mod):
		ocost = mod.cost
		if 'paired' in mod.keywords:
			mod.cost /= 2 
		rv = super()._check_install(mod)
		if rv and 'paired' in mod.keywords:
			mod.cost = ocost
		return rv

def CyberpunkItemFactory(proto, option):
	name = proto['name']
	kwords = proto['keywords']
	if name == 'Cyberarm Cyberdeck':
		return CyberarmCyberdeck(proto, option)
	if name == 'Popup Grenade Launcher':
		return SmartlinkOnly(proto, option)
	if name == 'Popup Melee Weapon':
		return PopupMeleeWeapon(proto, option)
	if name == 'Popup Ranged Weapon':
		return PopupRangedWeapon(proto, option)	
	if name == 'Spare Cyberarm':
		return SwapableArm(proto,option)
	if name == 'Smart Glasses' or name == 'Smart Lens':
		return CyberpunkSmartGlasses(proto,option)
	if 'weapon' in kwords:
		if 'ranged' in kwords:
			return CyberpunkGun(proto, option)
		elif 'melee' in kwords:
			return CyberpunkMeleeWeapon(proto, option)
	elif 'ammunition' in kwords:
		return CyberpunkAmmo(proto, option)
	elif 'cyberware' in kwords or 'borgware' in kwords:
		return Cyberware(proto, option)
	elif 'runner suit' in kwords:
		return BodyweightSuit(proto, option)
	elif 'armor' in kwords:
		return CyberpunkArmor(proto, option)
	elif 'software' in kwords:
		return CyberpunkSoftware(proto, option)
	elif 'cyberdeck' in kwords:
		if 'splitslots' in kwords:
			return CyberdeckSplitSlots(proto, option)
		else:
			return Cyberdeck(proto, option)
	elif 'vehicle' in kwords:
		return vehicle_factory(proto,option)
	elif 'vehicle upgrade' in kwords:
		return vehicle_upgrade_factory(proto,option)
	else:
		return PhysicalObject(proto,option)
	#raise RuntimeError('Unimplemented Object Type')

class CyberpunkMarketDB(PrototypeStore):
	def __init__(self):
		super().__init__(CyberpunkItemFactory, dbpath=db_path)
		self.add_basic_items()
		self.add_melee_weapons()
		self.add_ranged_weapons()
		self.add_ammo()
		self.add_cyberware()
		self.add_armor()
		self.add_netrunning()
		self.add_vehicles()

	def add(self, data, defaults, contract):
		sell_words = {
			'weapon' : 0.85,
			'armor' : 0,
			'cyberdeck' : 0.5,
			'cyberware' : 0.25,
			'street drug' : 1.0,
			'gear' : 0.25,
			'fashion' : 0.05,
			'vehicle' : 0.5,
			'chipware' : 0.5,
			'borgware' : 0.25
		}

		if not isinstance(data,list):
			data = [data]
		value = 0
		for itm in data:
			if value in itm: continue
			if not 'cost' in itm: continue
			for k,v in sell_words.items():
				if k in itm.get('keywords',[]):
					value = itm['cost'] * v
					break 
			itm['value'] = value
		super().add(data,defaults,contract)

	def add_basic_items(self):
		self.load_file(['things.yaml','gear.yaml',
			'fashion.yaml', 'weapon_mods.yaml',
			'services.yaml', 'drugs.yaml'],
			defaults=PhysicalObject.prototype_defaults(),
			contract=PhysicalObject.prototype_contract())

	def add_vehicles(self):
		self.load_file('vehicles.yaml',
			defaults=Vehicle.prototype_defaults(),
			contract=Vehicle.prototype_contract())
		self.load_file('vehicle_upgrades.yaml',
			defaults=VehicleUpgrade.prototype_defaults(),
			contract=VehicleUpgrade.prototype_contract())

	def add_cyberware(self):
		self.load_file('cyberware.yaml',
			defaults=Cyberware.prototype_defaults(),
			contract=Cyberware.prototype_contract())

	def add_melee_weapons(self):
		self.load_file(['melee_weapons.yaml', 'animal_weapons.yaml'], 
			defaults=CyberpunkMeleeWeapon.prototype_defaults(),
			contract=CyberpunkMeleeWeapon.prototype_contract())
			
	def add_ranged_weapons(self):
		self.load_file('ranged_weapons.yaml', 
			defaults=CyberpunkGun.prototype_defaults(),
			contract=CyberpunkGun.prototype_contract())

	def add_netrunning(self):
		self.load_file('cyberdeck.yaml',
			defaults=Cyberdeck.prototype_defaults(),
			contract=Cyberdeck.prototype_contract())
		self.load_file('software.yaml',
			defaults=CyberpunkSoftware.prototype_defaults(),
			contract=CyberpunkSoftware.prototype_contract())

	def add_ammo(self):
		with open (os.path.join(db_path,'ammo.yaml')) as fin:
			wdata = yaml.safe_load(fin)	
		forms = wdata['forms']
		kinds = wdata['kinds']
		data = wdata['indiv']

		for kind in kinds:
			for form in forms:
				if not form['available'] in kind['available']: continue
				box = copy(form)
				box.update(kind)
				if 'keywords' in kind and 'keywords' in form:
					box['keywords'] = kind['keywords'] + ', ' + form['keywords']
				box['name'] = box['entry_name'].format(kind = kind['name'])
				box['display_name'] = box['display_name'].format(kind = kind['name'])
				del box['available']
				del box['entry_name']
				if (kind['name'] == '') and (form['name'] == 'darts'):
					continue
				box['name'] = box['name'].strip()
				data.append(box)

		self.add(data, 
			defaults=CyberpunkAmmo.prototype_defaults(),
			contract=CyberpunkAmmo.prototype_contract())

	def add_armor(self):
		self.load_file('armor.yaml', 
			defaults=CyberpunkArmor.prototype_defaults(),
			contract=CyberpunkArmor.prototype_contract())		

	def catalog(self):
		X = {
			'ranged' : [],
			'melee' : [],
			'cyberware' : [],
			'vehicle' : [],
			'vehicle_upgrades' : [],
			'software' : [],
			'hardware' : [],
			'weapon_mods' : [],
			'gear' : [],
			'fashion' : [],
			'fashionware' : [],
			'drug' : [],
			'ammunition': [],
			'service' : [],
			'cyberdeck' : [],
			'armor' : [],
			'linear_frame' : [],
			'wheel_chair' : [],
			'animal_weapons' : [],
			'animal_armor' : []
		}
		for k,v in self.data.items():
			kwords = v['keywords']
			itm = (v['name'], v.get('option_hint',False))
			target = None
			if 'borgware' in kwords:
				target = 'cyberware'
			elif 'vehicle upgrade' in kwords:
				target = 'vehicle_upgrades'
			elif 'ranged weapon attachment' in kwords or 'scope' in kwords or 'magazine' in kwords:
				target = 'weapon_mods'
			elif 'linear frame' in kwords:
				target = 'linear_frame'
			elif 'wheelchair' in kwords:
				target = 'wheel_chair'
			elif 'natural' in kwords:
				if 'weapon' in kwords:
					target = 'animal_weapons'
				elif 'armor' in kwords:
					target = 'animal_armor'
			else:
				for word in ['vehicle upgrade', 'vehicle', 'cyberware', 'armor',
					'melee', 'ranged', 'software', 'hardware','fashionware', 'fashion', 'drug', 
					'ammunition', 'cyberdeck', 'service', 'gear']:
					if word in kwords:
						target = word 
						break 
			if target:
				X[target].append(itm)
		for k in X.keys():
			X[k].sort(key=lambda x: x[0])
		return X

CyberpunkMarket = CyberpunkMarketDB()
Catalog = CyberpunkMarket.catalog()




