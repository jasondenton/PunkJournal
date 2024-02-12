class UniversalSet(set):
	def __and__(self, other):
		return other

	def __rand__(self, other):
		return other

	def __or__(self, other):
		return self

	def __ror__(self, other):
		return self

	def __contains__(self, el):
		return True
