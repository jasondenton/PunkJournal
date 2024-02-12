from aliasdict import CaseIgnoreAliasDict
from cbexception import CharacterBuilderBadCommand 
from utils import group_by
from gameobj import PhysicalObject
from containers import InventoryContainer
from copy import deepcopy, copy 

DOESNOTHAVE = {
	'code' : 404,
	'message' : 'Character does not have {number} {item}(s).'
}
ALREADYDESIGNATED = {
	'code' : 405,
	'message' : 'There is already an item with designation {tag}.'
}
NOSUCHDESIGNATION = {
	'code' : 407,
	'message' : 'No such tag as {loc}.'
}
CANNOTATTACH = {
	'code' : 408,
	'message' : 'Cannot attach a {part} to a {item}.'
}
INVALIDDEST = {
	'code' : 4089,
	'message' : 'Cannot have a {item} in {location}.'
}

class CharacterInventory:
	class InventoryIterator:
		def __init__(self, inventory, keywords=None, locations=None, nested=True):
			self.inventory = inventory
			self.nested = nested
			if not keywords:
				self.keywords = set([])
			elif not isinstance(keywords, list):
				self.keywords = set([keywords])
			else:
				self.keywords = set(keywords)

			if not locations:
				self.locations = []
			elif not isinstance(locations, list):
				self.locations = [locations]
			else:
				self.locations = locations

		def __itm_matches__(self, itm):
			if len(self.keywords) > 0 and len(self.keywords & itm.keywords) < 1:
				return False 
			return True

		def __to_y__(self, itm):
			ml = []
			for c in itm.contents:
				if self.__itm_matches__(c):
					ml.append(c)
				ml += self.__to_y__(c)
			return ml

		def __call__(self):
			for (key, locdata) in self.inventory.locations.items():
				itm = self.inventory.desc[key]
				for (locname, count) in locdata.items(): 
					if len(self.locations) > 0 and not locname in self.locations: 
						continue
					itm.count = count
					if self.__itm_matches__(itm): 
						yield (itm, locname)
					if self.nested:
						ml = self.__to_y__(itm)
						for x in ml:
							yield(x, locname)	

	def __init__(self):
		self.locations = CaseIgnoreAliasDict() # name,  location, count ==> number at location
		self.desc = CaseIgnoreAliasDict() #name => descriptor
		self.designated = {}

	def inventory_view(self, keyword=None, location=None):
		it = self.InventoryIterator(self, keyword, location)
		return [x for (x,y) in it()]

	def inventory_by_location(self, keyword=None, location=None, nested=True):
		it = self.InventoryIterator(self, keyword, location, nested)
		return [(x,y) for (x,y) in it()]

	def local_item_descriptor(self, key):
		return self.desc.get(key,False)

	def default_location(self, itm):
		if 'stationary' in itm.keywords:
			return 'home'
		#if 'fashion' in itm.keywords:
		#	return 'worn'
		if 'vehicle' in itm.keywords:
			if itm.medium == 'air':
				return 'hanger'
			if itm.medium == 'water':
				return 'marina'
			return 'garage'
		if 'mount' in itm.keywords:
			return 'stable'
		return 'carried'

	def validate_location(self, loc, itm):
		if loc == 'worn':
			if 'worn' in itm.keywords: 
				return
			else:
				raise CharacterBuilderBadCommand(INVALIDDEST, item=itm, location=loc)
		if loc == 'carried':
			if not len({'stationary', 'vehicle'} & itm.keywords):
				return
			else:
				raise CharacterBuilderBadCommand(INVALIDDEST, item=itm, location=loc)

	def add(self, itm, number=1, location=None):
		key = itm.name
		if not location:
			location = self.default_location(itm)
		else:
			self.validate_location(location, itm)
		if not key in self.desc:
			self.desc[key] = itm
			self.desc.alias(key, itm.aliases)
			self.locations.alias(key, itm.aliases)
		if not key in self.locations:
			self.locations[key] = CaseIgnoreAliasDict()
		if not location in self.locations[key]:
			self.locations[key][location] = 0
		self.locations[key][location] += number 

	def have_or_error(self, key, number=1, location='carried'):
		onhand = self.locations.get(key, {}).get(location,0)
		if onhand < number:
			raise CharacterBuilderBadCommand(DOESNOTHAVE,item=key, number=number)
		return onhand

	def remove(self, key, number=1, location='carried'):
		onhand = self.have_or_error(key, number, location)
		onhand -= number
		if onhand == 0:
			del self.locations[key][location]
			if len(self.locations[key]) == 0:
				del self.locations[key]
				del self.desc[key]
		else:
			self.locations[key][location] = onhand

	def find(self, key, num=1):
		if not key in self.locations: return False
		if 'carried' in self.locations[key] and self.locations[key]['carried'] >= num:
			return 'carried'
		if 'worn' in self.locations[key] and self.locations[key]['worn'] >= num:
			return 'worn'
		for loc in self.locations[key].keys():
			if self.locations[key][loc] >= num: return loc 
		return False

	def designate(self, orig, tag):
		if tag in self.designated: 
			raise CharacterBuilderBadCommand(ALREADYDESIGNATED, item=tag)
		loc = self.find(orig)
		if not loc:
			raise CharacterBuilderBadCommand(DOESNOTHAVE, number='a', item=orig)
		itm = self.desc[orig]
		self.remove(orig,1,loc)
		itm = deepcopy(itm)
		if not 'display_name' in itm:
			itm.display_name = itm.name
		itm.name = tag
		self.designated[tag] = itm
		self.add(itm, 1, loc)
		return itm

	def attach(self, host, part):
		if not host in self.designated:
			raise CharacterBuilderBadCommand(NOSUCHDESIGNATION, loc=host)
		hostitm = self.designated[host]
		loc = self.find(part, 1)
		if not loc:
			if part in self.designated:
				hostitm.install(self.designated[part])
			else:
				raise CharacterBuilderBadCommand(DOESNOTHAVE, number='a', item=part)
		else:	
			hostitm.install(self.desc[part])
			self.remove(part,1,loc) 

	def render(self):
		ri = {}
		cw = 0.0
		vehicles = {}
		for (key, locdata) in self.locations.items():
			for (locname, count) in locdata.items(): 
					if not locname in ri:
						ri[locname] = []
					itm = self.desc[key]
					tmp = itm.render()
					tmp['count'] = count
					if locname in ['carried', 'worn'] :
						cw += itm.get_weight()
					if 'vehicle' in itm.keywords and locname in ['garage', 'hanger', 'marina']:
						if locname not in vehicles:
							vehicles[locname] = []
						vehicles[locname].append(tmp)
					else:
						ri[locname].append(tmp)
		if 'carried' in ri:
			ci = ri['carried']
			del ri['carried']
		else:
			ci = []
		if 'home' in ri:
			hm = ri['home']
			del ri['home']
		else:
			hm = []
		if 'worn' in ri:
			worn = ri['worn']
			del ri['worn']
		else:
			worn = []
		return {
			'worn' : worn,
			'carried_weight' : cw,
			'carried_inventory' : ci,
			'home_inventory' : hm,
			'other_locations' : ri,
			'vehicles' : vehicles
		}

	def __repr__(self):
		s = ''
		inv = self.by_location()
		for loc in inv:
			s += '{}\n============\n'.format(loc.capitalize())
			for i in inv[loc]:
				s += '{:3}   {}\n'.format(i[1],str(i[0]))
			s += '\n'
		s += 'Carried Weight: {:0.2}kg\n'.format(self.carry_weight())
		return s