from cbexception import CharacterBuilderBadCommand 
from copy import copy, deepcopy
from utils import normalize_display_name

NOTENOUGHSLOTS = {
	'code' : 104,
	'message' : 'Not enough open slots to install {attachment} in {item}.'
}
NOTCOMPATIBLE = {
	'code' : 105,
	'message' : 'Cannot install {attachment} in {item}.'
}
NOTINSTALLABLE = {
	'code' : 109,
	'message' : 'Item {item} cannot be installed in something else.'
}
ALREADYINSTALLED = {
	'code' : 110,
	'message' : 'Item {item} is already installed.'
}
ITEMNOTFOUND = {
	'code' : 111,
	'message' : 'The item {item} was not found at the given location.'
}

class PrototypedObject:
	@staticmethod
	def prototype_defaults():
		return  {
			'aliases' : [],
			'keywords' : [],
			'option' : False,
			'card' : None,
			'note' : [],
			'count' : 1,
			'sort' : 10
		}

	@staticmethod 
	def prototype_contract():
		return {
			'name' : str,
			'aliases' : set,
			'keywords' : set,
			'count' : int,
			'note' : list
		}

	def __init__(self, proto, option, *args, **kwargs):
		self.prototype = deepcopy(proto)
		self.option = option
		if 'rename' in proto:
			self.name = proto['rename'].format(**self.__dict__)
			self.name = normalize_display_name(self.name)
			#self.prototype['name'] = self.name

	def __bool__(self):
		return True 
		
	def __getattr__(self, key):
		if key in self.__dict__:
			return self.__dict__[key]
		if key in ['__getstate__','__setstate__']:
			return super().__getattr__(key)
		if key[0:2] == '__':
			return super().__getattr__(key)
		return self.prototype[key]

	def __setattr__(self, key, value):
		self.__dict__[key] = value
		return value

	def __contains__(self, key):
		if key in self.__dict__:
			return True
		if key in self.prototype:
			return True
		return False

	def __eq__(self, other):
		if other == None: return False
		if other == False: return False
		if self.prototype['name'] != other.prototype['name']:
			return False
		topt = self.get('option', None)
		if isinstance(topt, str):
			topt = topt.lower()
		oopt = other.get('option', None)
		if isinstance(oopt, str):
			oopt = topt.lower()
		return topt == oopt

	def __repr__(self):
		if self.__contains__('display_name'):
			return self.display_name.format(**self.__dict__)
		return self.name

	def __hash__(self):
		return id(self)

	def flatten(self):
		rv = copy(self.prototype)
		for k,v in self.__dict__.items():
			if k == 'prototype': continue
			rv[k] = v
		return rv 

	def get(self, key, df):
		if key in self.__dict__:
			return self.__dict__[key]
		if key in self.prototype:
			return self.prototype[key]
		return df

	def isa(self, thing):
		thing = thing.lower()
		if self.prototype['name'].lower() == thing: return True
		if thing in self.aliases: return True
		return False

	def nameopt_eq(self, name, option):
		name = name.lower()
		if isinstance(option, str):
			option = option.lower()
		myname = self.prototype['name'].lower()
		myopt = self.get('option', False)
		if isinstance(myopt, str):
			myopt = myopt.lower()
		if myopt == False: myopt = None
		if option == False: option = None
		if name != myname:
			return False
		return myopt == option 

	def render(self):
		if self.note:
			vs = self.flatten()
			n = [x.format(**vs) for x in self.note]
		else:
			n = []
		name = self.get('display_name', self.name)
		if self.option:
			opt = self.option.capitalize()
		else:
			opt = self.option
		name = name.format(option=opt)
		return {
			'name' : name,
			'keywords' : list(self.keywords),
			'notes' : n,
			'count' : self.count,
			'option' : self.option
		}
		
class NestableObject(PrototypedObject):
	@staticmethod
	def prototype_defaults():
		rv = PrototypedObject.prototype_defaults()
		rv.update({
			'holds' : [],
			'max_container_size' : 0,
			'install_in' : False,
			'needs_slots' : 1,
			'package' : False,
			'pass_notes' : True
		})
		return rv

	@staticmethod
	def prototype_contract():
		rv = PrototypedObject.prototype_contract()
		rv.update({
			'holds' : set,
			'max_container_size' : int,
			'needs_slots' : int
		})
		return rv

	def __init__(self, proto, option, *argc, **kwargs):
		super().__init__(proto, option)
		self.contents = []
		self.contained_in = []
		self.container_only = False
		self.used_slots = 0

	def __len__(self):
		return len(self.contents)

	def _check_install(self, itm):
		avail = self.max_container_size - self.used_slots
		if avail < itm.needs_slots:
			return CharacterBuilderBadCommand(NOTENOUGHSLOTS, attachment=itm.name, item=self.name)
		if not itm.install_in:
			return CharacterBuilderBadCommand(NOTINSTALLABLE,  item=itm.name)
		if not itm.install_in in self.holds:
			return CharacterBuilderBadCommand(NOTCOMPATIBLE, attachment=itm.name, item=self.name)
		for a in self.contents:
			if not a: continue
			if itm.prototype['name'] == a.prototype['name']:
				if not 'multiple' in itm.keywords:
					return CharacterBuilderBadCommand(ALREADYINSTALLED, item=itm)
		return False

	def can_install(self, itm):
		exp = self._check_install(itm)
		if not exp: return True
		for c in self.contents:
			if c.can_install(itm): return True
		return False

	def _put_item_into_container(self, itm):
		if 'stackable' in itm.keywords:
			for c in self.contents:
				if c == itm:
					c.count += 1
					return
		itm.contained_in.append(self)
		self.contents.append(itm)
		self.used_slots += itm.needs_slots

	def install(self, itm):
		error = self._check_install(itm)
		if error == False:
			self._put_item_into_container(itm)
			return
		for sub in self.contents:
			if sub.can_install(itm):
				sub.install(itm)
				return
		if self.get('proxy_for', False):
			self.proxy_for.install(itm)
			return
		raise error

	def find_match_by_name(self, name, option):
		mt = []
		for at in self.contents:
			if at.nameopt_eq(name, option):
				mt.append(at)
		for at in self.contents:
			mt += at.find_match_by_name(name, option)
		return mt

	def find_match_by_example(self, exp):
		mt = []
		for at in self.contents:
			if at == exp:
				mt.append(at)
		for at in self.contents:
			mt += at.find_match_by_example(exp)
		return mt

	def _remove_hook(self, itm):
		pass

	def _remove(self, itm):
		self.contents.remove(itm)
		itm.contained_in.remove(self)
		self.used_slots -= itm.needs_slots
		rv = self._remove_hook(itm)
		return rv

	def _remove_from_container(self, name, litm):
		if len(litm) == 0:
			raise CharacterBuilderBadCommand(ITEMNOTFOUND, item=name)
		itm = litm[0]
		if itm in self.contents:
			return self._remove(itm)
		for cont in self.contents:
			rv = cont.remove_from_container(itm)
			if rv: return rv 
		return False

	def remove_by_name(self, name, option):
		pos = self.find_match_by_name(name, option)
		return self._remove_from_container(name, pos)

	def remove_by_example(self, exp):
		pos = self.find_match_by_example(exp)
		return self._remove_from_container(exp.name, pos)	

	def __iter__(self):
		self.iter_idx = -1
		return self

	def __next__(self):
		if self.iter_idx == len(self.contents)-1: raise StopIteration
		self.iter_idx += 1
		if not self.contents[self.iter_idx]: return self.__next__()
		return self.contents[self.iter_idx]

	def _render_item(self):
		contents = self._render_container()
		if self.note:
			vs = self.flatten()
			n = [x.format(**vs) for x in self.note]
		else:
			n = []
		for c in contents:
			if c.get('pass_notes',True):
				n += c['notes']
		rv = super().render()
		rv.update({
			'contents' : contents,
			'notes' : n,
			'pass_notes' : self.get('pass_notes', True)
		})
		return rv

	@staticmethod
	def sort_function(itm):
		return itm.name 

	def _render_container(self):
		scnt = sorted(self.contents, key=self.sort_function)
		return [x.render() for x in scnt if x]


	def render(self):
		if self.container_only:
			return self._render_container()
		else:
			return self._render_item()

	def contents_with_keyword(self, keyword):
		rv = []
		if keyword in self.keywords:
			rv.append(self)
		for piece in self.contents:
			rv += piece.contents_with_keyword(keyword)
		return rv

class PhysicalObject(NestableObject):
	@staticmethod
	def prototype_defaults():
		rv = NestableObject.prototype_defaults()
		rv.update({
			'weight' : 0.0,
			'cost' : 0.0
		})
		return rv

	@staticmethod
	def prototype_contract():
		rv = NestableObject.prototype_contract()
		rv.update({
			'weight' : float,
			'cost' : float
		})
		return rv

	def get_weight(self):
		w = self.weight * self.count
		for c in self.contents:
			if 'selfcarry' in c.keywords:
				continue
			w += c.get_weight()
		return w  

	def _render_item(self):
		rv = super()._render_item()
		rv.update({
			'weight' : self.get_weight()
		})
		return rv
			

