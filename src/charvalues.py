from aliasdict import CaseIgnoreAliasDict
from gameobj import PrototypedObject
from cbexception import CharacterBuilderBadCommand 
from utils import parse_key, normalize_name
from copy import deepcopy

BADSTATVALUE = {
	'code' : 102,
	'message' : 'Value for {name} must be between {min} and {max}.'
}

BADINITIALVALUE = {
	'code' : 103,
	'message' : 'Value for {name} must start between {min} and {max}.',
}

NOSUCHITEM = {
	'code' : 101,
	'message': 'No such item as {item}.'
}

SETONCE = {
	'code' : 105,
	'message' : 'You may only set the initial value of {value} once.'
}

NOTDIRECT = {
	'code' : 103,
	'message' : 'You may not directly set the value of {value}.'
}


class CharacterValue(PrototypedObject):
	@staticmethod
	def prototype_defaults():
		rv = PrototypedObject.prototype_defaults()
		rv.update({
			'start_min' : 0,
			'start_max' : 9999,
			'min' : 0,
			'max' : 9999,
			'value' : None,
			'default' : 0,
			'start' : None
		})
		return rv

	@staticmethod 
	def prototype_contract():
		rv = PrototypedObject.prototype_contract()
		rv.update({
			'start_min' : int,
			'start_max' : int,
			'min' : int,
			'max' : int,
			'default' : int
		})
		return rv

	def __setattr__(self, key, vl):
		if key == 'value':
			rv = self.check_value(vl)
			if rv != False:
				raise rv 
			if self.value == None:
				self.start = vl
		return super().__setattr__(key,vl)

	def __repr__(self):
		return '{} = {}'.format(self.name, self.value)

	def render(self):
		if self.value == None:
			v = 0
		else:
			v = self.value 
		parts = self.name.split(':')
		return {
			'name' : self.get('display_name',self.name),
			'value' : v
		}

	def check_value(self, vl):
		if self.value == None:
			if vl < self.start_min or vl > self.start_max:
				return CharacterBuilderBadCommand(BADINITIALVALUE, name=self.name, min=self.start_min, max=self.start_max)
		if vl < self.min or vl > self.max:
			return CharacterBuilderBadCommand(BADSTATVALUE, name=self.name, min=self.start_min, max=self.start_max)
		return False

	def can_increment(self):
		if self.value == None:
			nv = 0 
		else:
			nv = self.value + 1 
		return not self.check_value(nv)

	def increment(self):
		nv = self.value + 1
		self.__setattr__('value', nv)

def DerivedValue(cls):
	class Wrapper(cls):
		def __init__(self, proto, option):
			super().__init__(proto,option)
			self.parts = []

		def add_part(self, pt):
			self.parts.append(pt)

		def __getattr__(self, key):
			if key == 'value':
				return self.value_formula()
			return super().__getattr__(key)

		def increment(self):
			raise CharacterBuilderBadCommand(NOTDIRECT, value=self.name)

		def can_increment(self):
			return False 
	return Wrapper

def SummedValue(cls):
	@DerivedValue
	class Wrapper(cls):
		def value_formula(self):
			accum = 0
			for p in self.parts:
				accum += p.value 
			return accum
	return Wrapper

class SetOnceCharacterValue(CharacterValue):
	def __init__(self, proto, option):
		super().__init__(proto, option)
		self.can_set = True

	def __getattr__(self, key):
		if key == 'value_as_num':
			v = super().__getattr__('value')
			if v == None: return 0
			return v 
		return super().__getattr__(key)

	def __setattr__(self, key, vl):
		if key == 'value':
			if not self.can_set and self.value != None:
				raise CharacterBuilderBadCommand(SETONCE,value=self.name)
			self.can_set = False 
		super().__setattr__(key,vl)

	def increment(self):
		nv = self.value_as_num + 1
		CharacterValue.__setattr__(self, 'value', nv)

class CharacterValues(CaseIgnoreAliasDict):
	def __init__(self, db):
		super().__init__()
		self.database = db

	def __contains__(self, key):
		key = normalize_name(key)
		if super().__contains__(key):
			return True
		if key in self.database:
			return True
		return False

	def __getitem__(self, key):
		key = normalize_name(key)
		if super().__contains__(key):
			return super().__getitem__(key)
		if not key in self.database:
			raise CharacterBuilderBadCommand(NOSUCHITEM, item=key)
		tmp = deepcopy(self.database[key])
		self.alias(tmp.name, tmp.aliases)
		self[tmp.name] = tmp
		return self[tmp.name]

	#def __setitem__(self, key, value):
	#	raise RuntimeError('here')
	#	tmp = self.__getitem__(key)
	#	tmp.value = value
	#	return value 

	def populate(self, doset=True):
		# sometimes specialized skills end up on the sheet pre-populate
		if doset:
			for k,v in self.items():
				if v.value == None:
					v.value = v.default 
		(reg, spec) = self.database.inventory()
		for key in reg:
			if key in self and self[key].value != None : continue
			v = self[key]
			if doset:
				v.value = v.default
			self.__setitem__(key, v)
		
	def render(self):
		rv = {}
		for k,v in self.data.items():
			rv[k] = v.render()
		return rv


	