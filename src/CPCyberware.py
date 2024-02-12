from cbexception import CharacterBuilderBadCommand 
from gameobj import NestableObject
from containers import Container, ContainerPair, PositionalContainer, InventoryContainer
from utils import parse_key
from CPHumanity import HumanityRecord
import re
from copy import copy

BASENOTINSTALLED = {
	'code' : 2001,
	'message' : 'Base cyberware not installed for {holds}.'
}
LOCATIONNOTUNDERSTOOD = {
	'code' : 2003,
	'message' : 'Install location {loc} not understood.'
}
EYENOTINSTALLED = {
	'code' : 2005,
	'message' : 'No Cybereye installed in the given position.'
}
BADEYEPOSITION = {
	'code' : 2002,
	'message' : 'Wrong number of positions trying to install {item}.'
}
PADALREADYINSTALLED = {
	'code' : 2017,
	'message' : 'You already have a {pad} installed.'
}
NONEEDSTD = {
	'code' : 2018,
	'message' : 'No need to install an extra {pad}'
}
LIMBCOVERED = {
	'code' : 2040,
	'message' : 'Limb already has a covering.'
}
NOQMOUNT = {
	'code' : 2041,
	'message' : 'Swapping a cyberlimb requires a quickchange mount in both limbs.'
}
NOTACYBERARM = {
	'code' : 2022,
	'message' : 'The item {item} is not a spare cyberarm.'
}
REMOVEAUDIOFIRST = {
	'code' : 2026,
	'message' : 'Remove Sensor Array before removng cyber audio suite.'
}
NOTINMEATLIMB = {
	'code' : 2019,
	'message' : 'Cannot install {item} in a meat limb.'
}
SENSORNEEDSAUDIO = {
	'code' : 2016,
	'message' : 'Sensor Array requies that a cyber audio suite be installed first.'
}
NOSUCHCHIP = {
	'code' : 2028,
	'message' : 'No chip named {chip} in chip library.'
}
NOSHOULDERMOUNT = {
	'code' : 2030,
	'message' : 'An Artifical Shoulder Mount is required to install borg arms.'
}
ALREADYHASFRAME = {
	'code' : 2031,
	'message' : 'Character already has a linear frame.'
}

ONESPEEDWARE = {
	'code' : 2315,
	'message' : 'Only one Speedware may be installed at a time.'
}

NOTINMEDICAL = {
	'code' : 2451,
	'message' : 'No options in medical grade cyberware'
}

#adds humanity_reocord= to param list
def CyberManager(cls):
	class WrapperCyberManager(cls):
		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
			self.humrec = kwargs.get('humanity_record', None)
			if not self.humrec: raise RuntimeError('CyberManager requires named parameter humanity_record be sent.')
			self.reduce_humanity = True
			self.position_code = 'x'

		def toggle_maxloss(self, tog):
			self.reduce_humanity = tog 

		def install(self, itm):
			super().install(itm)
			if not self.reduce_humanity: self.humrec.toggle_maxloss(False)
			if itm.get('humanity', 0) > 0:
				self.humrec.install_cyberware(itm)
			if not self.reduce_humanity: self.humrec.toggle_maxloss(True)

		def _remove_hook(self, itm):
			super()._remove_hook(itm)
			if not self.reduce_humanity: self.humrec.toggle_maxloss(False)
			if itm.get('humanity', 0) > 0:
				self.humrec.remove_cyberware(itm)
			if not self.reduce_humanity: self.humrec.toggle_maxloss(True)
			return itm

		@staticmethod
		def sort_function(cyb):
			if cyb.get('enables', False):
				return 0
			if 'pad' in cyb.keywords:
				return 1 
			if 'covering' in cyb.keywords:
				return 999
			if 'weapon' in cyb.keywords:
				return 299
			return 99

		def metadata(self):
			return {}

	return WrapperCyberManager	

#adds enabled=False to parmaeter list
def EnablingManager(cls):
	class WrapperEnabling(cls):
		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
			self.enabled = kwargs.get('enabled', False)

		def _check_install(self, itm):
			if not self.enabled and not itm.get('enables', False):
				return CharacterBuilderBadCommand(BASENOTINSTALLED, holds=itm.install_in)
			return super()._check_install(itm)

		def install(self, itm):
			if itm.get('enables', False):
				self.enabled = True
				if not self.can_install(itm):
					self.enabled = False
				else:
					itm.proxy_for = self  
			super().install(itm)

		def _remove_hook(self, itm):
			super()._remove_hook(itm)
			if itm.enables:
				cp = copy(self.contents)
				for c in cp:
					if not c: continue
					self.remove_by_example(c) 
				self.contents = []
				self.enabled = False
			return itm

		def disable(self):
			en = False
			for mod in self.contents:
				if mod.enables:
					self.remove_by_example(mod)
			self.enabled = False

		def shrink_to_fit(self):
			while self.used_slots > self.max_container_size:
				mod = self.contents[-1]
				self.remove_by_example(mod)

	return WrapperEnabling

@CyberManager
@EnablingManager
class CyberEnablingContainer(Container):
	pass

@CyberManager
class CyberwareContainer(Container):
	pass

@EnablingManager
class EnablingContainer(Container):
	@staticmethod
	def sort_function(cyb):
		if cyb.get('enables', False):
			return 0
		if 'pad' in cyb.keywords:
			return 1 
		if 'covering' in cyb.keywords:
			return 999
		if 'weapon' in cyb.keywords:
			return 299
		return 99

@ContainerPair
class PairedEnablingContainer(EnablingContainer):
	pass 

BORGEYEPATTERN = re.compile('(borg eye\s?)?(?P<e1>[12345lr])(?P<e2>[12345lr])?', re.IGNORECASE)
#BORGEYEPATTERN = re.compile('(?P<e1>[12345lr])(?P<e2>[12345lr])?', re.IGNORECASE)
@CyberManager
class CyberEyes(PairedEnablingContainer):
	def __init__(self, *args, **kwargs):
		super().__init__('Cybereyes', 3, ['cybereye'], enabled=False, **kwargs)
		self.eyes = {
			1   : EnablingContainer('Borg Eye 1', 3, ['cybereye'], enabled=False),
			2   : EnablingContainer('Borg Eye 2', 3, ['cybereye'], enabled=False),
			3   : EnablingContainer('Borg Eye 3', 3, ['cybereye'], enabled=False),
			4   : EnablingContainer('Borg Eye 4', 3, ['cybereye'], enabled=False),
			5   : EnablingContainer('Borg Eye 5', 3, ['cybereye'], enabled=False),
			'l' : self.left, 'L' : self.left,
			'r' : self.right, 'R' : self.right,		
		}
		self.borgeyes = False
		self.left.position_code = 'L'
		self.right.position_code = 'R'
		for i in range(1,6):
			self.eyes[i].position_code =  '%d' % i 

	def decode_eyeplace(self, pos):
		if pos == 'l': return self.left
		if pos == 'r': return self.right
		else: return self.eyes[int(pos)]

	def get_position(self, itm):
		placement = itm.option 
		if 'paired' in itm.keywords:
			need = 2
		else:
			need = 1
		places = []
		if placement:
			locdat = BORGEYEPATTERN.search(placement)
			if locdat:
				gd = locdat.groupdict()
				places.append(self.decode_eyeplace(gd['e1']))
				if gd['e2'] != None:
					places.append(self.decode_eyeplace(gd['e2']))
		if not placement:
			places = [self.left, self.right]
		if len(places) == 0:
			raise CharacterBuilderBadCommand(LOCATIONNOTUNDERSTOOD, loc=placement)
		elif len(places) == 1:
			if id(places[0]) == id(self.left):
				itm.option = 'left'
			elif id(places[0]) == id(self.right):
				itm.option = 'right'
			else:
				itm.option = places[0].name
		if len(places) != need:
			raise CharacterBuilderBadCommand(BADEYEPOSITION, item=itm)
		return places

	def install(self, itm):
		super().install(itm)
		if 'medical_grade' in itm.keywords:
			pos = self.get_position(itm)
			pos[0].max_container_size = 0 

	#because indiv remove calls endup in non-cyber mangers
	def remove_by_example(self, itm):
		super().remove_by_example(itm)
		self.humrec.remove_cyberware(itm)
		if 'medical_grade' in itm.keywords:
			pos = self.get_position(itm)
			pos[0].max_container_size = 3		
		
	def disable_mount(self):
		for i in range(1,6):
			self.eyes[i].disable()
		self.borgeyes = False

	def enable_mount(self):
		self.borgeyes = True

	#def borg_iter(self):
	#	tmp = []
	#	for i in range(1,6):
	#		tmp.append([x for x in self.eyes[i].__iter__()])
	#	return tmp.__iter__()

	def metadata(self):
		return {}

	def render(self):
		return {
			'Left Eye' : self.eyes['l'].render(),
			'Right Eye' : self.eyes['r'].render(),
			'Borg Eye 1' : self.eyes[1].render(),
			'Borg Eye 2' : self.eyes[2].render(),
			'Borg Eye 3' : self.eyes[3].render(),
			'Borg Eye 4' : self.eyes[4].render(),
			'Borg Eye 5' : self.eyes[5].render()
		}

class CyberLimbContainer(EnablingContainer):
	def __init__(self, name, holds, *args, enabled_size=0, **kwargs):
		super().__init__(name, 1, holds, *args, **kwargs)
		self.pad = None
		self.covering = None
		self.kind = 'meat'
		self.enabled_size = enabled_size
		self.disabled_size = 1

	def _check_install(self, itm):
		if self.kind == 'medical':
			return CharacterBuilderBadCommand(NOTINMEDICAL)
		if self.kind == 'meat' and not 'meat' in itm.keywords and not itm.enables:
			return CharacterBuilderBadCommand(NOTINMEATLIMB,item=itm)
		if 'pad' in itm.keywords and self.pad:
			return CharacterBuilderBadCommand(PADALREADYINSTALLED,pad=itm)
		if self.kind == 'cyber' and 'standard' in itm.keywords:
			return CharacterBuilderBadCommand(NONEEDSTD,pad=itm)
		if 'covering' in itm.keywords:
			if self.kind == 'meat':
				return CharacterBuilderBadCommand(NOMEATCOVER)
			elif self.covering:
				return CharacterBuilderBadCommand(LIMBCOVERED)
		return super()._check_install(itm)

	def _remove_hook(self, itm):
		if self.pad == itm:
			self.pad = None 
		if self.covering == itm:
			self.covering = None
		if itm.enables:
			self.go_meat()

	def install(self, itm):
		super().install(itm)
		if 'pad' in itm.keywords:
			self.pad = itm
		if 'covering' in itm.keywords:
			self.covering = itm 
		if itm.get('enables', False):
			if 'medical_grade' in itm.keywords:
				#by the time we get here, _remove_hook for the cyberarm has fired and called go_meat
				self.go_medical()
			else:
				self.go_cyber()

	def go_cyber(self):
		if self.pad and 'standard' in self.pad.keywords:
			self.remove_by_example(self.pad)
		self.kind = 'cyber'
		self.max_container_size = self.enabled_size

	def go_meat(self):
		self.kind = 'meat'
		self.max_container_size = self.disabled_size
		if self.covering:
			self.remove_by_example(self.covering)
		if self.pad:
			self.remove_by_example(self.pad)
		for mod in self.contents:
			if not 'meat' in mod.keywords:
				self.remove_by_example(mod)
		self.shrink_to_fit()

	def go_medical(self):
		self.kind = 'medical'
		self.max_container_size = 0
		if self.pad:
			self.remove_by_example(self.pad)
		if self.covering:
			self.remove_by_example(self.covering)					
		torm = [x for x in self.contents]
		for mod in torm:
			if 'medical_grade' in mod.keywords: continue
			self.remove_by_example(mod)

	def __iter__(self):
		enb = None
		srt = []
		for x in self.contents:
			if x.enables:
				enb = x
			elif x == self.pad or x == self.covering:
				continue
			else:
				srt.append(x)
		tmp = [enb] + [self.pad] + srt + [self.covering]
		tmp = [x for x in tmp if x]
		return tmp.__iter__()
		
	def render(self):
		if self.covering and not 'obvious' in self.covering.keywords:
			self.keywords - {'obvious'}
		return super().render() 

@CyberManager
class CyberArmContainer(CyberLimbContainer):
	def __init__(self, *args, neuroware_container=None, **kwargs):
		super().__init__('Arm', ['cyberarm'], *args, enabled_size=4, **kwargs)
		self.neuro = neuroware_container

	def check_snap(self):
		cost = 0
		qfound = False
		for mod in self.contents:
			if not mod: continue
			if mod.isa('Quickchange Mount'):
				qfound = True
			if mod.enables: continue
			if mod.humanity > 0:
				if 'borgware' in mod.keywords:
					cost += 4
				elif 'cyberware' in mod.keywords:
					cost += 2
		if not qfound:
			raise CharacterBuilderBadCommand(NOQMOUNT)
		return cost 

@ContainerPair
class CyberArmsContainer(CyberArmContainer):
	pass

@PositionalContainer
class AllArmsContainer:
	def __init__(self, humanity_record=None, neuroware_container=None):
		self.regular = CyberArmsContainer(humanity_record=humanity_record, neuroware_container=neuroware_container, enabled=True)
		self.borgarms = CyberArmsContainer(humanity_record=humanity_record, neuroware_container=neuroware_container, enabled=False)
		self.borgarms.left.go_cyber()
		self.borgarms.right.go_cyber()
		self.has_mount = False
		self.humrec = humanity_record
		self.regular.left.position_code = 'L'
		self.regular.right.position_code = 'R'
		self.borgarms.left.position_code = 'BL'
		self.borgarms.right.position_code = 'BR'

	def _check_install(self,itm):
		pos = self.get_position(itm)
		for p in pos:
			rv = p._check_install(itm)
			if rv: return rv
		return False

	def get_position(self, itm):
		if 'borg' in itm.option:
			if not self.has_mount:
				raise CharacterBuilderBadCommand(NOSHOULDERMOUNT)
			return self.borgarms.get_position(itm)
		else:
			return self.regular.get_position(itm)

	def swap_arms(self, spare, side, borg):
		if not spare.isa('Spare Cyberarm'):
			raise CharacterBuilderBadCommand(NOTACYBERARM,item=sparename)
		spare_cost = spare.check_snap()
		if borg:
			armpair = self.borgarms
		else:
			armpair = self.regular
		if side not in ['left', 'right']:
			raise CharacterBuilderBadCommand(LOCATIONNOTUNDERSTOOD,loc=side)
		cur_cost = armpair.__dict__[side].check_snap()
		outgoing = armpair.__dict__[side]
		armpair.__dict__[side] = spare
		armpair.__dict__[side].snap_on()
		outgoing.snap_off()
		adj_cost = cur_cost - spare_cost
		self.humrec.adjust_max_humanity(adjcost, 'Cyberarms Swapped.')
		return outgoing

	def enable_mount(self):
		self.has_mount = True

	def disable_mount(self):
		self.borgarms.left.disable()
		self.borgarms.right.disable()
		self.has_mount = False

	def __iter__(self):
		return self.regular.__iter__()

	def borg_iter(self):
		return self.borgarms.__iter__()

	def render(self):
		rv1 = self.regular.render()
		rv2 = self.borgarms.render()
		return {
			'Left Arm' : rv1['left'],
			'Right Arm' : rv1['right'],
			'Left Borgarm' : rv2['left'],
			'Right Borgarm' : rv2['right']
		}

	def metadata(self):
		spc = False
		carm = False
		for ptr in [self.regular, self.borgarms]:
			if ptr.left.kind == 'cyber' or ptr.right.kind == 'cyber':
				carm = True
			for ptr2 in [ptr.left.covering, ptr.right.covering]:
				if ptr2 and ptr2.isa('Cyberarm Superchrome Covering'):
					spc = True
		return {
			'cyberarm' : carm,
			'superchrome arm' : spc
		}

class CyberLegContainer(CyberLimbContainer):
	def __init__(self, *args, humanity_record=None, **kwargs):
		super().__init__('Leg', ['cyberleg'], *args, enabled_size=3, humanity_record=humanity_record, enabled=True, **kwargs)

@CyberManager
@ContainerPair
class _CyberLegsContainer(CyberLegContainer):
	pass 

class CyberLegsContainer(_CyberLegsContainer):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.left.position_code = 'L'
		self.right.position_code = 'R'

	#gotta wrap the previous level, to get a container that has access to left/right
	def render(self):
		return {
			'Left Leg' : self.left.render(),
			'Right Leg' : self.right.render()
		}

	#because indiv remove calls endup in non-cyber mangers
	def remove_by_example(self, itm):
		super().remove_by_example(itm)
		self.humrec.remove_cyberware(itm)

	def metadata(self):
		spc = False
		if self.left.covering and self.left.covering.isa('Cyberleg Superchrome Covering'): spc = True
		if self.right.covering and self.right.covering.isa('Cyberleg Superchrome Covering'): spc = True		
		return {
			'superchrome leg' : spc
		}

class AudioContainer(CyberEnablingContainer):
	def __init__(self, *args, **kwargs):
		super().__init__('Cyberaudio', 3, 'cyberaudio', humanity_record=kwargs['humanity_record'])
		self.sensor_array = False

	def _remove_hook(self, itm):
		super()._remove_hook(itm)
		if itm.enables and self.sensor_array:
			sa = self.find_match_by_name('Sensor Array')[0]
			self.remove_by_example(sa)
			self.disable_mount()

	def enable_mount(self):
		if not self.enabled:
			raise CharacterBuilderBadCommand(SENSORNEEDSAUDIO)
		self.sensor_array = True
		self.max_container_size += 5

	def disable_mount(self):
		self.sensor_array = False
		self.max_container_size -= 5
		self.shrink_to_fit()	

class BorgContainer(CyberwareContainer):
	def __init__(self, *args, eyes=None, audio=None, arms=None, humanity_record=None, **kwargs):
		super().__init__('Borgware', 99, 'borgware', *args, humanity_record=humanity_record, **kwargs)
		self.eyes = eyes
		self.audio = audio
		self.arms = arms
		self.linear_frame = False

	def install(self, itm):
		if self.linear_frame and 'linear frame' in itm.keywords:
			raise CharacterBuilderBadCommand(ALREADYHASFRAME)
		super().install(itm)
		if itm.isa('MultiOptic Mount'):
			self.eyes.enable_mount()
		elif itm.isa('Sensor Array'):
			self.audio.enable_mount()
		elif itm.isa('Artificial Shoulder Mount'):
			self.arms.enable_mount()
		if 'linear frame' in itm.keywords:
			self.linear_frame = True		

	def _remove_hook(self, itm):
		super()._remove_hook(itm)
		if itm.isa('MultiOptic Mount'):
			self.eyes.disable_mount()
		elif itm.isa('Sensor Array'):
			self.audio.disable_mount()
		elif itm.isa('Artificial Shoulder Mount'):
			self.arms.disable_mount()
		elif 'linear frame' in itm.keywords:
			self.linear_frame = False

	def metadata(self):
		return {
			'linear frame' : self.linear_frame
		}

class NeuralwareContainer(CyberEnablingContainer):
	def __init__(self, *args, **kwargs):
		super().__init__('Neuralware', 5, 'neuralware', humanity_record=kwargs['humanity_record'])
		self.speedware = False
		self.position_code = ''

	def _check_install(self, itm):
		if self.speedware != False and 'speedware' in itm.keywords:
			return CharacterBuilderBadCommand(ONESPEEDWARE)
		return super()._check_install(itm)

	def install(self, itm):
		super().install(itm)
		if 'speedware' in itm.keywords:
			self.speedware = itm

	def _remove_hook(self, itm):
		super()._remove_hook(itm)
		if 'speedware' in itm.keywords:
			self.speedware = False		

	def metadata(self):
		plugs = 0
		sockets = 0
		grips = 0
		pedit = False
		for mod in self.contents:
			if mod.isa('Interface Plugs'):
				plugs += 1
			if mod.isa('Chipware Socket'):
				sockets += 1
			if mod.isa('Subdermal Grip'):
				grips += 1
			if mod.isa('Pain Editor'):
				pedit = True
		smart_gun = (grips > 0 or plugs > 0)
		chips = []
		for socket in self.contents:
			if socket.isa('Chipware Socket'):
				for chip in socket.contents:
					chips.append(chip.render())
		if self.speedware:
			if self.speedware.isa('Kerenzikov Speedware'):
				sw = 'K'
			elif self.speedware.isa('Sandevistan Speedware'):
				sw = 'S'
		else:
			sw = False

		return {
			'interface plugs' : plugs,
			'chipware sockets' : sockets,
			'subdermal grips' : grips,
			'use smartgun' : smart_gun,
			'chips' : chips,
			'pain editor' : pedit,
			'speedware' : sw 
		}

class InternalCyberware(CyberwareContainer):
	def __init__(self, humanity_record):
		super().__init__('Internal Cyberwear', 7, 'internal', humanity_record=humanity_record)

	def metadata(self):
		grafts = 0 
		for mod in self.contents:
			if mod.isa('Grafted Muscle and Bone Lace'):
				grafts += 1
		return {
			'muscle grafts' : grafts
		}

class ChipwareLibrary(Container):
	def __init__(self, *args, **kwargs):
		super().__init__('Chipware', 99, 'chipware')
		self.position_code = ''

class FashionwareContainer(Container):
	def __init__(self):
		super().__init__('Fashion Ware', 7, 'fashionware')
		self.position_code = ''

	def metadata(self):
		tat = 0 
		skin = False
		hair = False
		for c in self.contents:
			if c.isa('Chemskin'):
				skin = True
			if c.isa('Techair'):
				hair = True
			if c.isa('Light Tattoo'):
				tat += 1
		return {
			'cool look' : skin and hair,
			'tattoo' : bool(tat > 2)
		}

CYBERSORTORDER = ['Neuralware', 'Internal', 'Cyberaudio', 
			'Left Eye', 'Right Eye', 'Borg Eye 1', 'Borg Eye 2', 'Borg Eye 3', 'Borg Eye 4', 'Borg Eye 5',
			'Left Arm', 'Left Borgarm', 'Right Arm', 'Right Borgarm', 
			'Left Leg', 'Right Leg', 'Borgware', 'External', 
			'Chipware', 'Fashionware']

class CyberpunkCyberbody:
	def __init__(self, humrec):
		neuro = NeuralwareContainer(humanity_record=humrec)
		eyes = CyberEyes(humanity_record=humrec)
		audio = AudioContainer(humanity_record=humrec)
		arms = AllArmsContainer(humanity_record=humrec, neuroware_container=neuro)

		self.designated = {
			'fashionware' : FashionwareContainer(),
			'internal' : InternalCyberware(humanity_record=humrec),
			'external' : CyberwareContainer('External Cyberwear', 7, 'external', humanity_record=humrec),
			'neuralware' : neuro,
			'chipware' : ChipwareLibrary(humanity_record=humrec),
			'cyberaudio' : audio,
			'cybereye' : eyes,
			'cyberarm' : arms,
			'borgware' : BorgContainer(humanity_record=humrec, eyes=eyes, audio=audio, arms=arms),
			'cyberleg' : CyberLegsContainer(humanity_record=humrec)
		}

	def all_cyberware(self):
		inven = InventoryContainer('Cyberware')
		simple = ['fashionware', 'internal', 'external', 'neuralware', 'cyberaudio', 'borgware']
		for cname in simple:
			inven.install(self.designated[cname])
		inven.install(self.designated['cyberarm'].regular.left)
		inven.install(self.designated['cyberarm'].regular.right)
		inven.install(self.designated['cyberarm'].borgarms.left)
		inven.install(self.designated['cyberarm'].borgarms.right)
		inven.install(self.designated['cyberleg'].left)
		inven.install(self.designated['cyberleg'].right)
		inven.install(self.designated['cybereye'].left)
		inven.install(self.designated['cybereye'].right)
		inven.install(self.designated['cybereye'].eyes[1])
		inven.install(self.designated['cybereye'].eyes[2])
		inven.install(self.designated['cybereye'].eyes[3])
		inven.install(self.designated['cybereye'].eyes[4])
		inven.install(self.designated['cybereye'].eyes[5])
		return inven 

	def sort_function(self, x):
		if x == '': return 0
		if x == 'L': return -3 
		if x == 'R': return -2
		if len(x) > 0 and x[0] == 'x': return -4
		return int(x)

	def concise(self):
		noreps = set()
		for c in self.all_cyberware():
			for itm in c:
				noreps.add(itm)
		preg = {}
		for itm in list(noreps):
			k = str(itm)
			pos = []
			for p in itm.contained_in:
				pos.append(p.position_code)
			if k in preg:
				preg[k] += pos 
			else:
				preg[k] = pos
		onelist = []
		for k in preg.keys():
			mult = preg[k].count('x')
			if mult == 1:
				preg[k] = []
			elif mult > 1:
				preg[k] = ['x%d' % mult]
			preg[k].sort(key=self.sort_function)
			preg[k] = ''.join(preg[k])
			if preg[k] == 'LR': preg[k] = ''
			if preg[k] != '':
				preg[k] = ' (' + preg[k] + ')'
			onelist.append(k + preg[k])
		onelist.sort()
		return onelist

	def metadata(self):
		exclude = ['chipware']
		meta = {}
		for k,v in self.designated.items():
			if k in exclude: continue
			meta.update(v.metadata())
		cware = self.all_cyberware()
		en = cware.contents_with_keyword('enhance')
		meta['cyber_enhancements'] = [e.boost for e in en]
		if meta['cool look']:
			meta['cyber_enhancements'].append('cool look')
		if meta['tattoo']:
			meta['cyber_enhancements'].append('tattoo')
		if meta['superchrome arm'] or meta['superchrome leg']:
			meta['cyber_enhancements'].append('superchrome')
		tools = cware.contents_with_keyword('tool')
		meta['tools'] = [t.boost for t in tools]
		meta['concise_list'] = self.concise()
		return meta

	def get_tags(self):
		#used to make sure designations still point at the right place post swap
		arms = self.designated['cyberarm']
		return {
			'left arm' : arms.regular.left,
			'right arm' : arms.regular.right,
			'left cyberarm' : arms.regular.left, 
			'right cyberarm' : arms.regular.right,
			'left borgarm' : arms.borgarms.left,
			'right borgarm' : arms.borgarms.right,
		}

	def slot_chip(self, chipname):
		(nm,opt) = parse_key(chipname)
		chip = self.designated['chipware'].find_match_by_name(nm,opt)
		if not chip:
			raise CharacterBuilderBadCommand(NOSUCHCHIP,chip=chipname)
		self.designated['neuralware'].install(chip[0])

	def render(self):
		rv = {}
		seen = set()

		for k,v in self.designated.items():
			tmp = self.designated[k].render()
			if isinstance(tmp, dict):
				rv.update(tmp)
			else:
				rv[k.capitalize()] = tmp
		rv2 = {}
		for key in CYBERSORTORDER:
			rv2[key] = rv[key]
			for x in rv2[key]:
				if not x['name'] in seen:
					seen.add(x['name'])
				else:
					x['notes'] = []

		return rv2
