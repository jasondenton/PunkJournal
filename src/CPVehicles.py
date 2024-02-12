from cbexception import CharacterBuilderBadCommand
from CPBaseObj import NonUpgradeableObject, UpgradeableObject

MAXUPGRADE = {
	'code' : 6342,
	'message' : 'The maximum number of {item} is already installed.'
}

SPECROOMS = {
	'code' : 3252,
	'message' : '{vehicle} requires specifying the number of rooms.'
}

SPECROOMS = {
	'code' : 3252,
	'message' : '{vehicle} requires specifying the number of rooms.'
}

NOTINTHISVEHICLE = {
	'code' : 2311,
	'message' : 'You can not install {item} in a {vehicle}.'
}

class VehicleBase(UpgradeableObject):
	@staticmethod
	def prototype_defaults():
		rv = UpgradeableObject.prototype_defaults()
		rv.update({
			'cost' : 1000,
			'moto' : 1
		})
		return rv

	@staticmethod
	def prototype_contract():
		rv = UpgradeableObject.prototype_contract()
		rv.update({
			'moto' : int
		})
		return rv

	def __init__(self, proto, option):
		super().__init__(proto, option)
		if self.moto >= 5:
			self.cost = 5000
			self.value = 4000
		else:
			self.cost = 1000
			self.value = 800

class VehicleUpgrade(VehicleBase):
	@staticmethod
	def prototype_defaults():
		rv = VehicleBase.prototype_defaults()
		rv.update({
			'install_in' : 'vehicle',
			'keywords' : set(['vehicle upgrade'])
		})
		return rv

class SmugglingUpgrade(VehicleUpgrade):
	def render(self):
		self.holsters = self.count * 2  
		if self.count > 1:
			self.plural = 's'
		else:
			self.plural = ''
		return super().render()

class HardPointUpgrade(VehicleUpgrade):
	def __init__(self, proto, option):
		super().__init__(proto,option)

	def _check_install(self, mod):
		if mod.prototype['name'] in ['Rhinemetall EMG-86 Railgun', 'Tsunami Arms Helix',  
			'Militech "Cowboy" U-56 Grenade Launcher']:
			return False
		return True

	def install(self, w):
		super().install(w)
		w.note += ['Weapon is turret mounted.']

class Vehicle(VehicleBase):
	@staticmethod
	def prototype_defaults():
		rv = VehicleBase.prototype_defaults()
		rv.update({
			'body_sp' : 0,
			'glass_sp' : 0,
			'speed' : 0,
			'seats' : 1,
			'rooms' : 0,
			'max_container_size': 99,
			'holds' : set(['vehicle']),
			'moto' : 1,
			'rooms' : 0,
			'cost' : 1000,
			'heavy' : False,
			'hardpoints' : 0,
			'family' : False,
			'pass_notes' : False,
			'allowed_upgrades' : ['complexity']
		})
		return rv

	@staticmethod
	def prototype_contract():
		rv = VehicleBase.prototype_contract()
		rv.update({
			'seats' : int,
			'speed' : int,
			'body_sp' : int,
			'glass_sp' : int,
			'move' : int,
			'moto' : int
		})
		return rv

	def install(self, mod):
		super().install(mod)
		if mod.isa('Armored Chassis'):
			self.body_sp = 13
		if mod.isa('Bulletproof Glass'):
			if self.glass_sp < 30:
				self.glass_sp += 15
			else:
				raise CharacterBuilderBadCommand(MAXUPGRADE, item=mod)
		if mod.isa('Seating Upgrade') or mod.isa('Ejection Seats'):
			self.seats += 2
		if mod.isa('Heavy Chassis'):
			self.sdp += 20
			self.keywords.add('heavy') 
		if mod.isa('Housing Capacity'):
			self.rooms += 1
			if self.rooms != 1:
				mod.note = []
		if mod.isa('Vehicle Heavy Weapon Mount'):
			self.hardpoints += 1

	def _check_install(self, itm):
		if not self.upgrade_class in itm.get('upgrade_class',''):
			return CharacterBuilderBadCommand(NOTINTHISVEHICLE, 
			item=itm.name, vehicle=self.prototype['name'])
		if itm.isa('Housing Capacity'):
			if self.rooms == 0 and not 'heavy' in self.keywords:
				return CharacterBuilderBadCommand(NOTINTHISVEHICLE, 
					item=itm.name, vehicle=self.prototype['name'])
		if 'heavy' in itm.keywords and not 'heavy' in self.keywords:
			return CharacterBuilderBadCommand(NOTINTHISVEHICLE, 
					item=itm.name, vehicle=self.prototype['name'])
		if itm.isa('Vehicle Heavy Weapon Mount'):
			if (self.rooms+1) == self.hardpoints:
				return CharacterBuilderBadCommand(NOTINTHISVEHICLE, 
					item=itm.name, vehicle=self.prototype['name'])
		return super()._check_install(itm)

	def weapon_or_upgrade(self, lst):
		for mod in lst:
			if mod.get('wkind', False):
				self.weapons.append(mod.render())
			else:
				self.upg.append(mod.render())
			if mod.pass_notes: 
				self.weapon_or_upgrade(mod.contents) 

	def render(self):
		rv = super().render()
		self.weapons = []
		self.upg = []
		self.weapon_or_upgrade(self.contents)
		rv.update({
			'move': self.move,
			'seats' : self.seats,
			'sdp' : self.sdp,
			'speed' : '{} kph'.format(self.speed),
			'body_sp': self.body_sp,
			'glass_sp' : self.glass_sp,
			'medium' : self.medium,
			'contents' : self.upg,
			'weapons' : self.weapons,
			'rooms' : self.rooms,
			'notes' : self.note
		})
		if self.family:
			rv['notes'].append('This is a family vehicle.')
		return rv

class AV9(Vehicle):
	def _check_install(self, mod):
		if mod.isa('Housing Capacity'):
			return CharacterBuilderBadCommand(NOTINTHISVEHICLE, 
			item=itm.name, vehicle=self.prototype['name'])
		return super()._check_install(self, mod)

class PersonalVehicle(Vehicle):
	def __init__(self, proto, option):
		super().__init__(proto,option)
		self.seating_upgrade = False 
		self.smuggling_upgrade = False 

	def _check_install(self, mod):
		if mod.isa('Smuggling Upgrade') and self.smuggling_upgrade:
			return CharacterBuilderBadCommand(MAXUPGRADE, item=mod.name)
		if (mod.isa('Seating Upgrade') or mod.isa('Ejection Seats')):
			return CharacterBuilderBadCommand(MAXUPGRADE, item='seats')
		return super()._check_install(mod)

	def install(self, mod):
		if mod.isa('Smuggling Upgrade') and self.smuggling_upgrade:
			self.smuggling_upgrade = True
		if (mod.isa('Seating Upgrade') or mod.isa('Ejection Seats')):
			self.seating_upgrade = True
		return super().install(mod)	

class RoomVehicle(Vehicle):
	def __init__(self, proto, option):
		super().__init__(proto,option)
		self.set_rooms()

	def set_rooms(self):
		ns = self.option.strip().split(' ')
		try:
			sz = int(ns[0])
		except:
			raise CharacterBuilderBadCommand(SPECROOMS, vehicle=self.name)
		self.rooms = sz
		self.seats = self.seats * sz 
		self.cost = self.cost * sz 
		self.option = '{} Rooms'.format(sz)

def vehicle_upgrade_factory(proto, option):
	if proto['name'] == 'Smuggling Upgrade':
		return SmugglingUpgrade(proto,option)
	if proto['name'] == 'Vehicle Heavy Weapon Mount':
		return HardPointUpgrade(proto,option)
	return VehicleUpgrade(proto,option)

def vehicle_factory(proto, option):
	if proto['name'] == 'AV-9 Super Aerodyne':
		return AV9(proto,option)
	if 'personal' in proto['keywords']:
		return PersonalVehicle(proto,option)
	if 'rooms' in proto['keywords']:
		return RoomVehicle(proto,option)
	return Vehicle(proto,option)

