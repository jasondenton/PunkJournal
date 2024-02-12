def group_by(lst, grouping=lambda x:x, sorting=lambda x:x, rev=False):
	'''Group a list into a list of sublists accordding to a grouping function.'''
	if len(lst) == 0: return []
	groups = []
	_lst = sorted(lst,key=sorting,reverse=rev)
	gval = grouping(_lst[0])
	nxtgp = [_lst[0]]
	for item in _lst[1:]:
		ngv = grouping(item)
		if not ngv or gval != ngv:
			groups.append(nxtgp)
			nxtgp = [item]
			gval = ngv
		else:
			nxtgp.append(item)
	groups.append(nxtgp)
	return groups

def parse_key(key):
	p = key.lower().split(':',1)
	key = p[0].strip()
	if len(p) > 1:
		opt = p[1].strip()
	else:
		opt = None
	return (key, opt)

def normalize_name(name):
	(key, opt) = parse_key(name)
	if opt:
		return '{}: {}'.format(key,opt)
	else:
		return key

def normalize_display_name(name):
	(key, opt) = parse_key(name)
	if opt:
		return '{}: {}'.format(key.capitalize(),opt.capitalize())
	else:
		return key.capitalize()	

def add_argument(func, arg2add):
	def wrapper(*args, **kwargs):
		return func(arg2add, *args, **kwargs)
	return wrapper


	