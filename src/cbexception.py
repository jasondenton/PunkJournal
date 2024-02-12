class CharacterBuilderBadCommand(RuntimeWarning):
	def __init__(self, error, **kwargs):
		self.code = error['code']
		self.message = error['message'].format(**kwargs)
		RuntimeWarning.__init__(self, self.message)
	
	def __str__(self):
		return self.message

	def dump(self):
		return {
			'code' : self.code,
			'message' : self.message
		}







	