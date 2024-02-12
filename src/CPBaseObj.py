from gameobj import PhysicalObject
from cbexception import CharacterBuilderBadCommand 

UPGRADENOTALLOWED = {
	'code' : 3425,
	'message' : 'You may not upgrade the {utype} of {item}.'
}

NOTUPGRADEABLE = {
	'code' : 2546,
	'message' : '{item} is not upgradeable.'
}

ALREADYUPGRADED = {
	'code' : 2457,
	'message' : 'That item tagged {item} has already been upgraded.'
}

NOSUCHUPGRADE = {
	'code' : 2345,
	'message' : 'Upgrade type {ukind} not understood; check the spelling and try again.'
}

UTYPEMAP = {
	'slots' : 'available slots',
	'armor' : 'stopping power',
	'conceal' : 'concealability',
	'humanity' : 'humanity cost',
	'quality' : 'quality',
	'complexity' : 'complexity'
}


class NonUpgradeableObject(PhysicalObject):
	def upgrade(self, up):
		raise CharacterBuilderBadCommand(NOTUPGRADEABLE, item=self.name)

class UpgradeableObject(PhysicalObject):
	def __init__(self, proto, option):
		super().__init__(proto, option)
		self.upgraded = False

	def upgrade(self, up):
		if up not in UTYPEMAP.keys():
			raise CharacterBuilderBadCommand(NOSUCHUPGRADE, ukind=up)
		uerr = UTYPEMAP[up]
		if self.upgraded:
			raise CharacterBuilderBadCommand(ALREADYUPGRADED, item=self.name)
		if not up in self.get('allowed_upgrades',[]):
			raise CharacterBuilderBadCommand(UPGRADENOTALLOWED, utype=uerr, item=self.name)
		if up == 'armor':
			if self.get('sp', -1) < 1:
				raise CharacterBuilderBadCommand(UPGRADENOTALLOWED, utype=uerr, item=self.name)
			self.sp += 1
		elif up == 'slots':
			if self.get('proxy_for', False):
				self.proxy_for.max_container_size += 1
			elif 'exotic' in self.keywords:
				self.max_container_size = 1 
				self.keywords.remove('exotic')
			else:
				self.max_container_size += 1
		elif up == 'humanity':
			if self.get('humanity', 0) < 2:
				raise CharacterBuilderBadCommand(UPGRADENOTALLOWED, utype=uerr, item=self.name)
			self.humanity -= 1
		elif up == 'conceal' :
			if self.get('concealable', -1) != -1:
				if self.concealable or self.get('hands', 2) == 1:
					raise CharacterBuilderBadCommand(UPGRADENOTALLOWED, utype=uerr, item=self.name)
			self.concealable = True
		elif up == 'quality' :
			if self.get('quality', 'not') != 'standard':
				raise CharacterBuilderBadCommand(UPGRADENOTALLOWED, utype=uerr, item=self.name)
			self.quality = 'excellent'
		elif up == 'complexity':
			self.display_name = 'Simplified ' + self.display_name
			self.note.append('If broken, this item may be fixed in half the usual time.')
			self.simpified = True
		self.upgraded = True 
