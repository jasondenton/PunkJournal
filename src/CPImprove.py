from ledger import CheckedLedger
from cbexception import CharacterBuilderBadCommand

NOTENOUGHIP = {
	'code' : 4500,
	'message' : 'Not enough IP to improve {option}.'
}

CANNOTIMPROVE = {
	'code' : 4501,
	'message' : 'You may not improve {value} by spending IP.'
}

MAXVALUE = {
	'code' : 4502,
	'message' : 'You have raised {value} to it\'s maximum value.'
}

class ImprovementLog(CheckedLedger):
	def __init__(self):
		super().__init__('Improvement Log', NOTENOUGHIP)

	def initial_build(self, values):
		stats = []
		skills = []
		role = None 
		rolesub = []
		for (n,v) in values.items():
			if v.start  == 0: continue
			p = (v.name, v.start)
			if 'stat' in v.keywords:
				stats.append(p)
			if 'skill' in v.keywords:
				skills.append(p)
			if 'role ability' in v.keywords:
				role = p 
			if 'role sub' in v.keywords:
				rolesub.append(p)
		stats.sort(key=lambda x: x[0])
		skills.sort(key=lambda x: x[0])
		rolesub.sort(key=lambda x: x[0])
		self.starting = {
			'stats' : stats,
			'skills' : skills,
			'role' : [role] + rolesub
		}

	def render(self):
		rv = super().render()
		tmp = self.starting['stats'] + self.starting['skills'] + self.starting['role']
		block = []
		for i in range(0,len(tmp)-1,2):
			block.append(tmp[i:i+2])
		block[-1].append(('',''))
		return {
			'initial_build' : block,
			'log' : rv,
			'available' : self.balance
		}
		
	def improve(self, value):
		cost = -1
		if 'role sub' in value.keywords:
			cost = 0 
		elif 'skill' in value.keywords:
			cost = 1
			if 'hard' in value.keywords:
				cost = 2 
		elif 'role ability' in value.keywords:
			cost = 3
		if cost < 0:
			raise CharacterBuilderBadCommand(CANNOTIMPROVE, value=value.name)
		if not value.can_increment():
			raise CharacterBuilderBadCommand(MAXVALUE, value=value.name)
		if value.value == None:
			value.value = 0
		nval = value.value + 1
		cost *= nval * -20
		memo = 'Raised {} to {}'.format(value.name, nval)
		self.add_entry(cost, memo, value.name)
		value.increment()

	def game_session(self, memo, ip):
		self.add_entry(ip, 'Game Session: {}'.format(memo), None)

