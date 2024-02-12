from inventory import CharacterInventory, NOSUCHDESIGNATION
from cbexception import CharacterBuilderBadCommand
from copy import deepcopy 
from utils import parse_key 

class CyberpunkInventory(CharacterInventory):
	def __init__(self, cb):
		super().__init__()
		self.cyberware = cb

	def upgrade(self, tag, utype):
		if not tag in self.designated:
			raise CharacterBuilderBadCommand(NOSUCHDESIGNATION, loc=tag)
		target = self.designated[tag]
		target.upgrade(utype)
		return target

	def designate(self, orig, tag):
		if tag in self.designated: 
			raise CharacterBuilderBadCommand(ALREADYDESIGNATED, item=tag)

		(name, opt) = parse_key(orig)
		cyber = self.cyberware.all_cyberware()
		itms = cyber.find_match_by_name(name,opt)
		itms = [x for x in itms if x.name == x.prototype['name']]
		if not itms:
			return super().designate(orig, tag)
		itm = itms[0]
		if not 'display_name' in itm:
			itm.display_name = itm.name
		self.designated[tag] = itm
		itm.name = tag
		return itm