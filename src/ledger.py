from dataclasses import dataclass
from cbexception import CharacterBuilderBadCommand 

@dataclass
class LedgerEntry:
	amount: float = 0
	memo: str = ''
	balance: int = 0
	date: str = ''

	def __repr__(self):
		return '{:10}     {:35}     {:9.2f}\t{:10.2f}'.format(self.date, self.memo, self.amount, self.balance)

	def render(self):
		return {
			'amount' : self.amount,
			'memo' : self.memo,
			'balance' : self.balance,
			'date' : self.date 
		}

class Ledger:
	def __init__(self, lname):
		self.ledger = []
		self.balance = 0
		self.name = lname
		self.date = ''

	def __iter__(self):
		self.iter_idx = -1
		return self

	def __next__(self):
		if self.iter_idx == len(self.ledger)-1: raise StopIteration
		self.iter_idx += 1
		return self.ledger[self.iter_idx]

	def __float__(self):
		return float(balance)

	def __int__(self):
		return int(balance)

	def __repr__(self):
		r = ['Available Balance: {:0.02f}\n============='.format(self.balance)]
		r += [str(x) for x in self.ledger]
		return '\n'.join(r)

	def add_entry(self, amount, memo=''):
		self.balance = self.balance + amount
		le = LedgerEntry(amount=amount, balance=self.balance, memo=memo, date=self.date)
		self.ledger.append(le)

	def render(self):
		return [e.render() for e in self.ledger]

class CheckedLedger(Ledger):
	def __init__(self, lname, exp):
		super().__init__(lname)
		self.exception = exp

	def add_entry(self, amount, memo='', opt=None):
		tbal = self.balance + amount
		if tbal < 0:
			raise CharacterBuilderBadCommand(self.exception, option=str(opt))
		super().add_entry(amount, memo)

class BankAccount(CheckedLedger):
	def __init__(self):
		super().__init__('Bank Account', 
			{
				'code' : 203,
				'message' : 'Character does not have enough cash to buy {option}.'
			})

	def adjust_last_entry(self, amount):
		self.ledger[-1].amount += amount
		self.ledger[-1].balance += amount
		self.balance += amount

	def can_afford(self, cost):
		return cost <= self.balance

class EmptyLedger:
	def __init__(self):
		self.balance = 0.0

	def __iter__(self):
		return self

	def __next__(self):
		raise StopIteration

	def __float__(self):
		return 0.0

	def __int__(self):
		return 0

	def __repr__(self):
		return 'Empty Ledger'

	def add_entry(self, amount, memo='', opt=None):
		pass

	def render(self):
		return []

class BottomlessBankAccount(EmptyLedger):
	def adjust_last_entry(self, amount):
		pass 

	def can_afford(self, cost):
		return True
		


