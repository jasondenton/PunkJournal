from collections import UserDict

class AliasDict(UserDict):
	def __init__(self):
		super().__init__()
		self.aliases = {}
		self.aliases_back = {}

	def key2cname(self, key):
		if key in self.data:
			return key 
		elif key in self.aliases:
			return self.aliases[key]
		else:
			return key

	def alias(self, cname, aliases):
		for alias in aliases:
			self.aliases[alias] = cname
		self.aliases_back[cname] = aliases

	def __getitem__(self, key):
		return self.data[self.key2cname(key)]

	def __delitem__(self, key):
		cname = self.key2cname(key)
		for a in self.aliases_back.get(cname,[]):
			del self.aliases[a]
		if cname in self.aliases_back:
			del self.aliases_back[cname]
		del self.data[cname]

	def __contains__(self, key):
		return (self.key2cname(key) in self.data)

	def __setitem__(self, key, value):
		self.data[self.key2cname(key)] = value

	def get(self, fkey,df):
		ckey = self.key2cname(fkey)
		if not ckey in self.data:
			return df 
		else:
			return self.data[ckey]

class CaseIgnoreAliasDict(AliasDict):

	def key2cname(self, key):
		if isinstance(key,str):
			key = key.lower()
		return super().key2cname(key)

	def alias(self, cname, aliases):
		tmp = []
		for a in aliases:
			if isinstance(a, str):
				a = a.lower()
			tmp.append(a)
		super().alias(cname.lower(), tmp)