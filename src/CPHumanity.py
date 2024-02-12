from ledger import CheckedLedger, EmptyLedger
from math import floor

OUTOFHUMANITY = {
	'code' : 1012,
	'message' : 'Adding more cyberware will give the character CyberPsychosis.'
}

class HumanityRecord:
	def __init__(self):
		self.current = CheckedLedger('Current Humanity', OUTOFHUMANITY)
		self.max = CheckedLedger('Max Humanity', OUTOFHUMANITY)
		self.domax = True
		
	@staticmethod
	def roll_dice(num):
		if num < 1:
			return 2
		return floor(num * 3.5)

	def add_entry(self, camt, mamt, memo):
		if not self.domax: mamt = 0
		self.current.add_entry(camt, memo);
		self.max.add_entry(mamt,memo)
		self.adjust_current_for_max()

	def toggle_maxloss(self, onoff):
		self.domax = onoff

	def humanity_event(self, amount, memo):
		self.add_entry(amount, 0, memo)

	def adjust_current_for_max(self):
		current = self.current.balance 
		mx = self.max.balance
		if current <= mx: return
		self.current.balance = mx
		self.current.ledger[-1].balance = mx 

	def install_cyberware(self, itm, date=''):
		curloss = HumanityRecord.roll_dice(itm.humanity) * -1
		kwords = itm.get('keywords', [])
		if 'cyberware' in kwords: 
				maxloss = -2
		elif 'borgware' in kwords:
				maxloss = -4
		else:
			maxloss = 0
		if 'paired' in kwords:
			maxloss *= 2
		memo = 'Installed {}'.format(str(itm))
		self.add_entry(curloss, maxloss, memo)
		
	def remove_cyberware(self, itm, date=''):
		if 'borgware' in itm.keywords:
			mx = 4
		elif 'cyberware' in itm.keywords:
			mx = 2
		if 'paired' in itm.keywords:
			mx *= 2
		memo = 'Removed {}.'.format(str(itm))
		self.add_entry(0, mx, memo)

	def gain_humanity(self, date, memo, dice):
		curgain = HumanityRecord.roll_dice(dice)
		self.add_entry(curgain, 0, memo)

	def current_humanity(self):
		hum = self.current.balance
		mx = self.max.balance
		emp = floor(hum / 10)
		return (emp, hum, mx)

	def adjust_max_humanity(self, amt, memo):
		self.add_entry(0,amt,memo)

	def starting_empathy(self, emp):
		hum = emp * 10
		self.add_entry(hum, hum, 'Starting Humanity')

	def __iter__(self):
		self.current.__iter__()
		self.max.__iter__()
		return self

	def set_date(self, date):
		self.current.date = date 
		self.max.date = date 

	def __next__(self):
		cur = self.current.__next__()
		mx = self.max.__next__()
		return {
			'date' : cur.date,
			'memo' : cur.memo,
			'current_loss' : cur.amount,
			'current_humanity' : cur.balance,
			'max_loss' : mx.amount,
			'max_humanity' : mx.balance
		}

	def render(self):
		return [x for x in self]

class NoHumanityRecord(HumanityRecord):
	def __init__(self):
		self.current = EmptyLedger()
		self.max = CheckedLedger('Max Humanity', OUTOFHUMANITY)
		self.domax = True
		super().starting_empathy(8)

	def starting_empathy(self, emp):
		self.empathy = emp

	def current_humanity(self):
		mx = self.max.balance	
		hum = min(mx, self.empathy * 10)
		emp = floor(hum / 10)
		return (emp, hum, mx)

class AnimalHumanityRecord(HumanityRecord):
	def __init__(self):
		self.current = EmptyLedger()
		self.max = EmptyLedger()
		self.domax = True

	def starting_empathy(self, emp):
		self.empathy = emp

	def current_humanity(self):
		emp = self.empathy
		mx = emp * 10
		hum = mx
		return (emp, hum, mx)