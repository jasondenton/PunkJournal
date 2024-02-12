from gameobj import NestableObject, PhysicalObject
from cbexception import CharacterBuilderBadCommand
from universalset import UniversalSet

LEFTORRIGHT = {
	'code' : 201,
	'message' : 'You must specify "left" or "right" to install {item}.',
}

class Container(NestableObject):
	def __init__(self, name, mxsz, holds, *args, **kwargs):
		if isinstance(holds, str):
			holds = [holds]
		super().__init__({
			'name' : name,
			'max_container_size' : mxsz,
			'holds' : set(holds),
			'needs_slots' : 1,
			'keywords' : set()
		}, False)
		self.container_only = True
	
def PositionalContainer(cls):
	class WrapperPositional(cls):
		def _check_install(self, mod):
			pos = self.get_position(mod)
			for p in pos:
				x = p._check_install(mod)
				if not x: return x
			return False

		def can_install(self, itm):
			exp = self._check_install(itm)
			if not exp:
				return True
			return False

		def install(self, itm):
			exp = self._check_install(itm)
			if exp: raise exp
			pos = self.get_position(itm)
			for p in pos:
				p.install(itm)

		def remove_by_example(self, itm):
			pos = self.get_position(itm)
			for p in pos:
				p.remove_by_example(itm)

#		def remove_by_name(self, name, option):
#			pos = self.getpos(itm)
#			for p in pos:
#				if itm in p.attached:
#					real = p.remove(itm)
#			return real
	return WrapperPositional

class InventoryContainer(PhysicalObject):
	def __init__(self, name):
		super().__init__({
			'name' : name,
			'max_container_size' : 9999,
			'holds' : UniversalSet(),
			'needs_slots' : 1,
			'weight' : 0.0,
			'keywords' : set(['multiple']),
			'count' : 1
		}, False)
		self.container_only = True

	def _check_install(self, itm):
		return False

	def install(self,itm):
		self.contents.append(itm)

def ContainerPair(cls):
	@PositionalContainer
	class WrapperContainerPair:
		def __init__(self, *args, **kwargs):
			self.left = cls(*args, **kwargs)
			self.right = cls(*args, **kwargs)

		def get_position(self, mod):
			if 'paired' in mod.keywords:
				return [self.left, self.right]
			if not mod.option:
				raise CharacterBuilderBadCommand(LEFTORRIGHT, item=mod.name)
			if 'left' in mod.option:
				return [self.left]
			if 'right' in mod.option:
				return [self.right]
			raise CharacterBuilderBadCommand(LEFTORRIGHT, item=mod.name)

		def find_match(self, name, option):
			return self.left.find_match(name, option) + self.right.find_match(name, option)

		def __len__(self):
			return 2

		def remove(self, itm):
			super().remove(itm)

		def __iter__(self):
			llist = [x for x in self.left]
			rlist = [x for x in self.right]
			return [llist, rlist].__iter__()

		def render(self):
			return {
				'left' : self.left.render(),
				'right' : self.right.render()
			}
			
	return WrapperContainerPair

@ContainerPair
class PairedContainer(Container):
	pass
