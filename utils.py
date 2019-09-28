
_counter = 0
# 58 character alphabet used in base58 encoding
_base58_alphabet = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


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