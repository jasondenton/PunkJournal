class Prerequisite:
	def __init__(self, reqs):
		self.reqs = reqs

	@staticmethod
	def _check_number(p, crec):
		return int(crec[p[0]]) >= p[1]

	@staticmethod
	def _check_string(p, crec):
		return str((crec[p[0]])).lower() == p[1].lower()

	@staticmethod
	def _check(p, crec):
		i = 0
		while i < len(p):
			if isinstance(p[i+1], str):
				r = Prerequisite._check_string(p[i:i+2], crec)
			elif isinstance(p[i+1], int):
				r = Prerequisite._check_number(p[i:i+2], crec)
			else:
				raise RuntimeError('Did not understand prerequisite {}'.format(p))
			if r:
				return True
			i += 2
		return False

	def check(self, sheet):
		for r in self.reqs:
			if not Prerequisite._check(r,sheet):
				return False
		return True


#crec = {
#	'body' : 5,
#	'will' : 6,
#	'role' : 'medtech'
#}

#p1 = Prerequisite([
#	['body', 4]
#])

#p2 = Prerequisite([
#	['body', 7]
#])

#p3 = Prerequisite([
#	['body',8,'will',2],
#	['role', 'solo']
#])

#p4 = Prerequisite([
#	['body',8,'will',2],
#	['role', 'medtech']
#])

#print(p1.check(crec))
#print(p2.check(crec))
#print(p3.check(crec))
#print(p4.check(crec))




