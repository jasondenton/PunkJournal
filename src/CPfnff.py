import yaml 
import os 

from utils import group_by
from math import ceil 
from prereq import Prerequisite

class ArmorStack:
	def __init__(self, armors):
		armors.sort(key=lambda x: x.sort) 
		self.sp = 0
		self.penalty = 0
		self.layers = []
		for armor in armors:
			self.sp = max(armor.get('sp', 0), self.sp)
			self.penalty = min(armor.get('penalty', 0), self.penalty)
			self.layers.append(str(armor))

	def render(self):
		return {
			'layers' : self.layers,
			'penalty' : self.penalty,
			'sp' : self.sp
		}

class FNFF:
	def __init__(self, csheet):
		self.cyber = csheet.cyberware.all_cyberware()
		self.csheet = csheet
		self.cmeta = csheet.cyberware.metadata()
		self.can_smartlink = self.cmeta['use smartgun']
		stats = csheet.values
		body = csheet.values['body'].effective 
		will = csheet.values['will'].effective
		self.luck = stats['luck'].effective
		self.hitpoints =  ceil((will + body) / 2.0) * 5 + 10
		self.woundthreshold = ceil(self.hitpoints/2.0)
		self.woundleft = self.hitpoints - self.woundthreshold
		self.deathsave = min(body, 10)
		self.armor()
		self.weapons()
		self.ammo()
		self.shields()
		self.unarmed()
		self.initative()

	def calc_tohit(self, weapons):
		for weapon in weapons:
			weapon_bonus = weapon.accuracy
			if self.can_smartlink and weapon.get('has_smartlink', False):
				weapon_bonus += 1
			sk = self.csheet.values[weapon.skill].effective
			tohit = weapon_bonus + sk
			weapon.tohit = tohit
			if weapon.get('autofire', 0) > 0:
				weapon.auto_tohit = self.csheet.values['autofire'].effective + weapon_bonus
			else:
				weapon.auto_tohit = 0
			self.calc_tohit(weapon.get('weapons',[]))

	def weapons(self):
		self.weapons = self.csheet.inventory.inventory_view(keyword='weapon', location='carried')
		self.weapons += self.cyber.contents_with_keyword('weapon')
		self.calc_tohit(self.weapons)
		self.weapons = [x for x in self.weapons if not x.get('is_attached', False)]
		
		vehicles = self.csheet.inventory.inventory_view(keyword='vehicle')
		vweapons = []
		for v in vehicles:
			vweapons += v.contents_with_keyword('weapon')
		self.calc_tohit(vweapons)

		self.vis_weapons = []
		for w in self.weapons:
			if not w.concealable:
				self.vis_weapons.append(w.get('display_name',w.name))

		self.has_natural_weapons = False 
		for w in self.weapons:
			if 'natural' in w.keywords:
				self.has_weapons = True
			
	def armor(self):
		self.armor = self.csheet.inventory.inventory_view(keyword='armor', location='worn')
		if len(self.armor) < 1:
			self.armor = self.csheet.inventory.inventory_view(keyword='armor', location='carried')
		self.armor += self.cyber.contents_with_keyword('armor')
		if len(self.armor) > 0:
			self.has_armor = True 
		else:
			self.has_armor = False
		self.helmet = ArmorStack([a for a in self.armor if 'helmet' in a.keywords])
		self.body = ArmorStack([a for a in self.armor if 'body' in a.keywords])
		for st in ['move', 'reflexes', 'dexterity']:
			self.csheet.values[st].set_penalty(self.body.penalty)

	def shields(self):
		self.shields = self.csheet.inventory.inventory_view(keyword='shield', location='carried')
		self.shields += self.cyber.contents_with_keyword('shield')
		if len(self.shields) > 0:
			self.has_armor = True

	def ammo(self):
		ammo = self.csheet.inventory.inventory_view(keyword='ammunition', location='carried')
		lstoflst = group_by(ammo, grouping=lambda x: x.ammo_class, sorting=lambda x: x.ammo_class)
		tmp = {}
		for akind in lstoflst:
			tmp[akind[0].ammo_class] = akind
		corder = ['medium pistol', 'heavy pistol', 'very heavy pistol', 'rifle', 'trounds', 
			'flechette', 'shotgun', 'darts', 'bolts', 'arrows', 'paint', 'flamer', 
			'battery', 'grenade', 'rocket', 'spike strip']
		self.ammo_pool = {}
		for c in corder:
			if c in tmp:
				self.ammo_pool[c] = tmp[c]

	def martial_style(self, name, dam):
		mdat = MARTIAL_ARTS_DATA.get(name.lower(),{})
		moves = mdat.get('moves',[])
		usable_moves = []
		for move in moves:
			if move.get('prerequisite', False):
				p = Prerequisite(move['prerequisite'])
				if not p.check(self.csheet.values):
					continue
			usable_moves.append(move)
		return {
			'name' : name.capitalize(),
			'tohit' : self.csheet.values['martial arts: ' + name].effective,
			'damage' : dam,
			'moves' : usable_moves,
			'ap' : True
		}

	def unarmed(self):
		ma_damage = self.csheet.values['body'].unarmed_damage()
		if self.cmeta['cyberarm'] and ma_damage < 2:
			brawl_damage = 2 
		else:
			brawl_damage = ma_damage

		if self.csheet.animal:
			self.unarmed_fighting = []
		else:
			self.unarmed_fighting = [{
				'name' : 'Brawling',
				'tohit' : self.csheet.values['Brawling'].effective,
				'damage' : brawl_damage,
				'moves' : [], #MARTIAL_ARTS_DATA['brawling']['moves'],
				'ap' : False
			}]

		for k,v in self.csheet.values.items():
			if v.prototype['name'] == 'Martial Arts':
				self.unarmed_fighting.append(self.martial_style(v.option, ma_damage))
		if len(self.unarmed_fighting) > 1:
			self.unarmed_fighting[1:].sort(key=lambda x:x['tohit'])
			self.unarmed_fighting[1]['moves'] = MARTIAL_ARTS_DATA['__share']['moves'] + self.unarmed_fighting[1]['moves']

	def initative(self):
		self.inote = ''
		self.inum = self.csheet.values['Reflexes'].effective
		if self.inum >= 8:
			self.dodge_bullets = self.csheet.values['evasion'].effective
		else:
			self.dodge_bullets = -1
		if self.cmeta['speedware'] == 'K':
			self.inum += 2
		elif self.cmeta['speedware'] == 'S':
			self.inote = '+3 if speedware is active.'

	def render(self):
		apool = {}
		for nm,knd in self.ammo_pool.items():
			apool[nm] = [k.render() for k in knd]

		return {
			'weapons' : [w.render() for w in self.weapons],
			'shields' : [s.render() for s in self.shields],
			'has_armor' : self.has_armor,
			'body_armor' : self.body.render(),
			'head_armor' : self.helmet.render(),
			'armor_penalty' : self.body.penalty,
			'ammunition' : apool,
			'hitpoints' : self.hitpoints,
			'woundthreshold' : self.woundthreshold,
			'woundleft' : self.woundleft,
			'fnff_luck' : self.luck,
			'deathsave' : self.deathsave,
			'unarmed_fighting' : self.unarmed_fighting,
			'initiative' : self.inum,
			'init_note' : self.inote,
			'dodge_bullets' : self.dodge_bullets,
			'visible_weapons' : self.vis_weapons,
			'armor_pieces' : [a.render() for a in self.armor]
		}

def load_martial_arts():
	db_path = os.environ['PUNKJOURNALDB']
	mdat = {}
	with open(os.path.join(db_path,'martial_arts.yaml')) as fin:
		ldat = yaml.safe_load(fin)
	for m in ldat:
		mdat[m['name'].lower()] = m
	return mdat 

MARTIAL_ARTS_DATA = load_martial_arts()

