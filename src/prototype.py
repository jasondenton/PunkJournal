import yaml
from copy import deepcopy
import os 
from utils import parse_key
from universalset import UniversalSet
from aliasdict import CaseIgnoreAliasDict
from cbexception import CharacterBuilderBadCommand 

MUSTHAVEOPTION = {
	'code' : 106,
	'message' : 'Item {item} requires an option to be set.',
}
INVALIDOPTION = {
	'code' : 107,
	'message' : 'Item {item} requires an option which must be one of {optset}.',
}
MUSTNOTHAVEOPTION = {
	'code' : 108,
	'message' : 'Item {item} does not allow an option to be specified.',
}
NOSUCHITEM = {
	'code' : 101,
	'message': 'No such item as {item}.'
}

def prototype_factory(prototype, defaults=None, contract=None):
	def make_set(proto, key):
		data = proto.get(key, [])
		if isinstance(data, set):
			return 
		elif isinstance(data, bool):
			if data:
				proto[key] = UniversalSet()
			else:
				proto[key] = False #makes error checking more complicated but better error messages
			return
		elif data == None:
			data = []
		elif isinstance(data, str):
			data = [x.strip() for x in data.lower().split(',')]
		if not isinstance(data, list):
			raise RuntimeError('Attempt to create a set from {}. Context: {}'.format(data, str(proto)))
		proto[key] = set(data)

	def check_against_schema(subj, schema):
		for k,v in schema.items():
			if not k in subj:
				raise RuntimeError('No key {} in {}'.format(str(k),str(subj)))
			if not isinstance(subj[k], v):
				raise RuntimeError('Key {} must be a {} in {}.'.format(str(k), v, str(subj)))

	if defaults:
		proto = deepcopy(defaults)
	else: 
		proto = {}
	proto.update(prototype)
	if proto['option'] == 'optional':
		pass
	elif isinstance(proto['option'], str):
			make_set(proto, 'option')
	if contract:
		for k,v in contract.items():
			if v == set:
				make_set(proto, k)	
			if v == float:
				proto[k] = float(proto[k])
			if v == list:
				if not isinstance(proto[k], list):
					proto[k] = [proto[k]]
		check_against_schema(proto, contract)
	return proto 

class PrototypeStore(CaseIgnoreAliasDict):
	def __init__(self, fact, dbpath=None):
		super().__init__()
		self.factory = fact 
		self.dbpath = dbpath

	def load_file(self, databases, defaults={}, contract={}):
		if isinstance(databases,str):
			databases = [databases]
		for file in databases:
			fpath = os.path.join(self.dbpath,file)
			with open(fpath, encoding='utf8') as fin:
				data = yaml.safe_load(fin)
			for p in data:
				self.add(p, defaults, contract)

	def add(self, items, defaults={}, contract={}):
		if not isinstance(items, list):
			items = [items]
		for itm in items:
			proto = prototype_factory(itm, defaults, contract)
			self[proto['name']] = proto
			self.alias(proto['name'], proto['aliases'])

	@staticmethod
	def _check_option(proto, opt):
		if proto['option'] == 'optional':
			return
		if not proto['option'] and not opt:
			return
		if proto['option']:
			if not opt:
				raise CharacterBuilderBadCommand(MUSTHAVEOPTION, item=proto['name'])
			if isinstance(proto['option'],set):
				if not opt in proto['option']:
					raise CharacterBuilderBadCommand(INVALIDOPTION, item=proto['name'], optset=str(proto['option']))
		else: #not proto and opt
			raise CharacterBuilderBadCommand(MUSTNOTHAVEOPTION, item=proto['name'])

	def __getitem__(self, fkey):
		(key, opt) = parse_key(fkey)
		if not super().__contains__(key):
			raise CharacterBuilderBadCommand(NOSUCHITEM,item=key)
		proto = super().__getitem__(key)
		PrototypeStore._check_option(proto, opt)
		itm = self.factory(proto, opt)
		return itm

	def __contains__(self, fkey):
		(key, opt) = parse_key(fkey)
		return super().__contains__(key)

	def __delitem__(self, key):
		raise RuntimeError('Cannot remove from PrototypeStore.')

	def inventory(self):
		opt = []
		nopt = []
		for (k,itm) in self.data.items():
			if itm['option']:
				opt.append(itm['name'])
			else:
				nopt.append(itm['name'])
		return (nopt,opt)

	def contents_of_store(self):
		names = []
		for (k,itm) in self.data.items():
			n = itm['name']
			if itm['option'] != False:
				n += '*'
			names.append(n)
		return names

	def debug(self):
		ns = self.contents_of_store()
		for n in ns:
			print(n)

