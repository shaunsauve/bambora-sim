
from collections import OrderedDict


_counter = 0
# 58 character alphabet used in base58 encoding
_base58_alphabet = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


class LimitedSizeDict(OrderedDict):
	def __init__(self, *args, **kwargs):
		self.size_limit = kwargs.pop("size_limit", None)
		OrderedDict.__init__(self, *args, **kwargs)
		self._check_size_limit()

	def __setitem__(self, key, value):
		OrderedDict.__setitem__(self, key, value)
		self._check_size_limit()

	def _check_size_limit(self):
		if self.size_limit is not None:
			while len(self) > self.size_limit:
				self.popitem(last=False)


def b58encode_int(i, default_one=True):
	if not i and default_one:
		return _base58_alphabet[0:1]
	string = b""
	while i:
		i, idx = divmod(i, 58)
		string = _base58_alphabet[idx:idx + 1] + string
	return string.decode('utf-8')


def next_count():
	global _counter
	_counter += 1
	return _counter


def dict_filter(d, only=None, exclude=None):
	"""
	:param d: dictionary to filter
	:param only: a list of keys to include (omitting all others).
	:param exclude: a list of keys to omit in the new dict Can be used with only but expected usage is one
		or the other
	:return: new filtered dictionary

	examples:
	dict_filter({'a':1, 'b': 2, 'c': 3}, only=['b'])
	{'b': 2}

	dict_filter({'a':1, 'b': 2, 'c': 3}, exclude=['b'])
	{'a': 1, 'c': 3}
	"""
	new_dict = {}
	exclude = set(exclude) if exclude is not None else []

	for k, v in d.items():
		# if not empty, then only include items in this list (unless they are also excluded)
		if only:
			if (k in only) and (k not in exclude):
				new_dict[k] = d[k]
		# otherwise include everything except the excluded
		else:
			if k not in exclude:
				new_dict[k] = d[k]

	return new_dict