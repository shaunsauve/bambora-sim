#!/usr/bin/env python3

import argparse
import sys
import time
from datetime import datetime

import jsonpickle
from flask import Flask, request, jsonify, Response

from limited_size_dictionary import LimitedSizeDict
from utils import b58encode_int, next_count

RECORD_LIMIT = 5000

# 6 digit encoded epoch time when the server instance was started
_serial = b58encode_int(int(time.time()))
_card_records = LimitedSizeDict(size_limit=RECORD_LIMIT)
_profile_records = LimitedSizeDict(size_limit=RECORD_LIMIT)
_payment_records = LimitedSizeDict(size_limit=RECORD_LIMIT)
_strict_mode = False

app = Flask(__name__)


def _generate_bogus_bamdora_token(prefix, seed):
	# bambora example: "a11-b02846fb-626c-4939-8c73-e26415be8d0d"
	return f"{prefix}-{_serial}-{str(next_count()).zfill(4)}-{datetime.utcnow().strftime('%d%m%Y-%H%M-%S%f')}-{seed[-4:]}"


@app.route('/scripts/tokenization/tokens', methods=['POST'])
def endpoint_tokenize_card():
	# a single use token
	new_card_token = _generate_bogus_bamdora_token('C', request.json['number'])
	new_card_record = {
		'request': request.json,
		'response': {
			'token': new_card_token,
			'code': 1,
			'version': 1,
			'message': ''
		}
	}
	if _strict_mode:
		_card_records[new_card_token] = new_card_record
	return jsonify(new_card_record['response'])


@app.route('/v1/profiles', methods=['POST'])
def endpoint_create_profile():
	# a multi-use token
	card_token = request.json['token']['code']

	if _strict_mode:
		card_record = _card_records.get(card_token, None)
		if not card_record:
			return jsonify({'message':f"unknown card token '{card_token}'"}), 422

	new_profile_token = _generate_bogus_bamdora_token('P', card_token)
	new_profile_record = {
		'request': request.json,
		'response': {
			'code': 1,
			'message': '',
			'customer_code': new_profile_token,
			'validation':  {
				'id': '',
				'approved': 1,
				'message_id': 1,
				'message': '',
				'auth_code': '',
				'trans_date': '',
				'order_number': '',
				'type': '',
				'amount': 100,
				'cvd_id': 1
			}
		}
	}
	if _strict_mode:
		_profile_records[new_profile_token] = new_profile_record
	return jsonify(new_profile_record['response'])


@app.route('/v1/payments', methods=['POST'])
def endpoint_create_payment():
	if request.json['payment_method'] != 'payment_profile':
		return jsonify({'message':'can only simulate payment_profile payments'}), 422

	profile_token = request.json['payment_profile']['customer_code']

	if _strict_mode:
		profile_record = _profile_records[profile_token]
		if not profile_record:
			return jsonify({'message':f"unknown customer code '{profile_token}'"}), 422

		card_record = _card_records[profile_record['request']['token']['code']]
	else:
		card_record = {
			'request': {
				"number": '4030000010001234',
				"expiry_month": "06",
				"expiry_year": "19",
				"cvd": "123"
			},
			'response': {
				'token': _generate_bogus_bamdora_token('C', '4030000010001234'),
				'code': 1,
				'version': 1,
				'message': ''
			}
		}

	new_payment_id = 10000000 + next_count()
	semi_canned_payment_response = {
		"id": new_payment_id,
		"authorizing_merchant_id": 367410000,
		"approved": "1",
		"message_id": "1",
		"message": "Approved",
		"auth_code": "TEST",
		"created": datetime.utcnow().isoformat(),
		"order_number": "1521750069",
		"type": "P",
		"payment_method": "CC",
		"risk_score": 0,
		"amount": request.json['amount'],
		"custom": {
			"ref1": "",
			"ref2": "",
			"ref3": "",
			"ref4": "",
			"ref5": ""
		},
		"card": {
			"card_type": "VI",
			"last_four": {card_record['request']['number'][-4:]},
			"address_match": 0,
			"postal_result": 0,
			"avs_result": "0",
			"cvd_result": "5",
			"avs": {
				"id": "U",
				"message": "Address information is unavailable.",
				"processed": False
			}
		},
		"links": [
			{
				"rel": "void",
				"href": f"https://api.na.bambora.com/v1/payments/{new_payment_id}/void",
				"method": "POST"
			},
			{
				"rel": "return",
				"href": f"https://api.na.bambora.com/v1/payments/{new_payment_id}/returns",
				"method": "POST"
			}
		]
	}
	new_payment_record = {
		'request': request.json,
		'response': semi_canned_payment_response
	}
	if _strict_mode:
		_payment_records[new_payment_id] = new_payment_record

	# standard json library can't handle nested lists, so pull out the big guns
	json_body = jsonpickle.encode(new_payment_record['response'])
	return Response(json_body)


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument(
		'-s', '--strict', help="enable strict mode which caches records and check for valid tokens", action='store_true')
	args = vars(parser.parse_args())
	_strict_mode = args.get('strict', False)

	app.run(host='0.0.0.0', port=80)
