#!/usr/bin/env python3

import argparse
import time
from faker import Faker
from datetime import datetime
import re
import logging

import jsonpickle
from flask import Flask, request, jsonify, Response

from utils import b58encode_int, next_count, LimitedSizeDict, dict_filter

RECORD_LIMIT = 5000

# 6 digit encoded epoch time when the server instance was started
_serial = b58encode_int(int(time.time()))
_card_records = LimitedSizeDict(size_limit=RECORD_LIMIT)
_profile_records = LimitedSizeDict(size_limit=RECORD_LIMIT)
_payment_records = LimitedSizeDict(size_limit=RECORD_LIMIT)

_strict_mode = False
_enable_cache = True

logger = logging.getLogger(__name__)
app = Flask(__name__)


"""
	see https://dev.na.bambora.com/docs/references/payment_APIs/v1-0-5/

	ProfileResponse {
		code : number
		message : string
		customer_code : string
		validation : CardValidation {
			id : string
			approved : integer
			message_id : integer
			message : string
			auth_code : string
			trans_date : string
			order_number : string
			type : string
			amount : number
			cvd_id : integer
		}
	}
	
	PaymentProfileResponse {
		code : integer
		message : string
		customer_code : string
		status : string
		last_transaction : string
		modified_date : string
		language : string
		velocity_group : string
		profile_group : string
		account_ref : string
		card : GetProfileDefaultCard {
			name : string
			number : string
			expiry_month : string
			expiry_year : string
			card_type : string
		}
		billing : Address {
			name : string
			address_line1 : string
			address_line2 : string
			city : string
			province : string
			country : string
			postal_code : string
			phone_number : string
			email_address : string
		}
		custom : Custom {
			ref1 : string
			ref2 : string
			ref3 : string
			ref4 : string
			ref5 : string
		}
	}
	

	ErrorResponse {
		code : integer
			category : integer
			message : string
			reference : string
			details : array of Detail {
			field : string
			message : string
		}
		validation : CardValidation {
			id : string
			approved : integer
			message_id : integer
			message : string
			auth_code : string
			trans_date : string
			order_number : string
			type : string
			amount : number
			cvd_id : integer
		}
	}
"""


def _generate_bogus_bamdora_token(prefix, seed):
	# genuine bambora example: "a11-b02846fb-626c-4939-8c73-e26415be8d0d"
	return f"{prefix}-{_serial}-{str(next_count()).zfill(4)}-{datetime.utcnow().strftime('%d%m%Y-%H%M-%S%f')}-{seed[-4:]}"


def _create_new_card_record(data):
	new_card_token = _generate_bogus_bamdora_token('C', data['number'])
	new_card_record = dict(data)
	new_card_record['token'] = new_card_token
	return new_card_record


def _generate_bogus_card_record(token=None):
	cc = Faker().credit_card_full().split('\n')
	card_type = re.split('[!\d]+', cc[0])[0].strip()
	number, expiry = cc[2].split()
	return {
		'token': token or _generate_bogus_bamdora_token('C', number),
		'name': cc[1],
		'number': number,
		'expiry_month': expiry.split('/')[0],
		'expiry_year': expiry.split('/')[1],
		'card_type': card_type,
		'cvc': cc[3].split()[1]
	}


def _generate_empty_card_record(token=None):
	return {
		'token': token or _generate_bogus_bamdora_token('C', '0000000000000000'),
		'name': '',
		'number': '0000000000000000',
		'expiry_month': '12',
		'expiry_year': '99',
		'card_type': ''
	}


def _generate_bogus_billing_address(card_record=None):
	fake = Faker()
	state = fake.state_abbr()
	return {
		'name': card_record['name'] if card_record else fake.name(),
		'address_line1': fake.street_address(),
		'address_line2': '',
		'city': fake.city(),
		'province': state,
		'country': fake.country(),
		'postal_code': fake.zipcode_in_state(state),
		'phone_number': fake.phone_number(),
		'email_address': fake.email()
	}


def _generate_empty_billing_address(card_record=None):
	return {
		'name': card_record['name'] if card_record else '',
		'address_line1': '',
		'address_line2': '',
		'city': '',
		'province': '',
		'country': '',
		'postal_code': '',
		'phone_number': '',
		'email_address': ''
	}


def _create_new_profile_record(customer_code=None, billing_address=None, card_record=None, language=None):
	card_record = card_record or _generate_empty_card_record()
	card_record['card_id'] = 1
	return {
		'customer_code': customer_code or _generate_bogus_bamdora_token('P', card_record['token']),
		'cards': [card_record],
		'billing': billing_address or _generate_empty_billing_address(card_record),
		'status': '',
		'last_transaction': '',
		'modified_date': datetime.utcnow(),
		'language': language or Faker().language_code(),
		'velocity_group': '',
		'profile_group': '',
		'account_ref': ''
	}


def _generate_bogus_profile_record(customer_code=None, card_record=None):
	return _create_new_profile_record(
		customer_code, _generate_bogus_billing_address(), card_record or _generate_bogus_card_record())


@app.route('/scripts/tokenization/tokens', methods=['POST'])
def endpoint_tokenize_card():
	"""
	body parameter:
		TokenRequest {
			number* : string
			expiry_month* : string
			expiry_year* : string
			cvd* : string
		}
	"""
	new_card_record = _create_new_card_record(request.json)
	if _enable_cache:
		_card_records[new_card_record['token']] = new_card_record

	new_card_response = {
		'token': new_card_record['token'],
		'code': 1,
		'version': 1,
		'message': ''
	}
	return jsonify(new_card_response)


@app.route('/v1/profiles', methods=['POST'])
def endpoint_create_profile():
	"""
	body parameter:
		ProfileBody {
			card : ProfileFromCard {
				name* : string
				number* : string
				expiry_month* : string
				expiry_year* : string
				cvd : string
			}
			token : ProfileFromToken {
				name* : string
				code* : string
			}
			billing : Address {
				name : string
				address_line1 : string
				address_line2 : string
				city : string
				province : string
				country : string
				postal_code : string
				phone_number : string
				email_address : string
			}
			custom : Custom {
				ref1 : string
				ref2 : string
				ref3 : string
				ref4 : string
				ref5 : string
			}
			language : string
			comment : string
			validate : boolean
		}

	responses:
		200	The Profile.	ProfileResponse
		400	Bad Request	ErrorResponse
		401	Authentication Failure	ErrorResponse
		402	Business Rule Violation or Decline	ErrorResponse
		403	Authorization Failure	ErrorResponse
		405	Invalid Request Method	ErrorResponse
		500	Internal Server Error	ErrorResponse
	"""

	# profile from card
	if request.json.get('card'):
		card_record = _create_new_card_record(request.json['card'])
		card_token = card_record['token']
	# profile from token
	else:
		card_token = request.json['token']['code']
		card_record = _card_records.get(card_token, None)
		if not card_record:
			if _strict_mode:
				return jsonify({'message': f"unknown card token '{card_token}'"}), 400
			card_record = _generate_empty_card_record(card_token)

	new_profile_record = _create_new_profile_record(
		request.json.get('billing', None), card_record, request.json.get('language', None))

	if _enable_cache:
		_profile_records[new_profile_record['customer_code']] = new_profile_record

	new_profile_response = {
		'code': 1,
		'message': '',
		'customer_code': new_profile_record['customer_code'],
		'validation': {
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
	return jsonify(new_profile_response)


@app.route('/v1/profiles/<profile_id>')
def endpoint_get_profile(profile_id):
	"""
	profile id is a.k.a customer code

	responses:
		200	The Profile.	PaymentProfileResponse
		400	Bad Request	ErrorResponse
		401	Authentication Failure	ErrorResponse
		402	Business Rule Violation or Decline	ErrorResponse
		403	Authorization Failure	ErrorResponse
		405	Invalid Request Method	ErrorResponse
		500	Internal Server Error	ErrorResponse
	"""

	profile_record = _profile_records.get(profile_id, None)
	if not profile_record:
		if _strict_mode:
			return jsonify({'message': f"unknown customer code '{profile_id}'"}), 400
		profile_record = _generate_bogus_profile_record(profile_id)

	response = dict_filter(profile_record, only=[
		'customer_code', 'status', 'last_transaction', 'modified_date', 'language', 'velocity_group', 'profile_group',
		'account_ref', 'billing'])

	response.update({
		'code': 1,
		'message': '',
		'card': profile_record['cards'][0]
	})
	return jsonify(response)


@app.route('/v1/profiles/<profile_id>/cards')
def endpoint_get_profile_cards(profile_id):
	profile_record = _profile_records.get(profile_id, None)
	if not profile_record:
		if _strict_mode:
			return jsonify({'message': f"unknown customer code '{profile_id}'"}), 400
		profile_record = _generate_bogus_profile_record(profile_id)

	cards = []
	for cc in profile_record['cards']:
		cards.append(dict_filter(cc, exclude=['cvc']))

	response = {
		'customer_code': profile_record['customer_code'],
		'code': 1,
		'message': '',
		'card': cards
	}
	return Response(jsonpickle.encode(response))


@app.route('/v1/payments', methods=['POST'])
def endpoint_create_payment():
	if request.json['payment_method'] != 'payment_profile':
		return jsonify({'message':'can only simulate payment_profile payments'}), 400

	profile_token = request.json['payment_profile']['customer_code']
	profile_record = _profile_records.get(profile_token, None)
	if not profile_record:
		if _strict_mode:
			return jsonify({'message': f"unknown customer code '{profile_token}'"}), 400
		card_record = _create_new_card_record()
		profile_record = _generate_bogus_profile_record(profile_token, card_record)
		if not profile_token:
			profile_token = profile_record['customer_code']
	else:
		try:
			card_record = profile_record['cards'][request.json['payment_profile']['card_id'] - 1]
		except:
			if _strict_mode:
				return jsonify({'message': f"invalid card id '{request.json['payment_profile']['card_id']}'"}), 400
			card_record = _generate_empty_card_record()

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
			"last_four": {card_record['number'][-4:]},
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
	if _enable_cache:
		_payment_records[new_payment_id] = new_payment_record

	# standard json library can't handle nested lists, so pull out the big guns
	json_body = jsonpickle.encode(new_payment_record['response'])
	return Response(json_body)


if __name__ == '__main__':
	logger.setLevel(logging.DEBUG)
	parser = argparse.ArgumentParser()
	parser.add_argument(
		'-s', '--strict', help="enable strict mode which check for valid tokens against cached records", action='store_true')
	parser.add_argument('-n', '--nocache', help="do not cache records", action = 'store_true')
	args = vars(parser.parse_args())
	_strict_mode = args.get('strict', False)
	_enable_cache = not args.get('nocache', False)

	logger.error({'strict_mode': _strict_mode, 'enable_cache': _enable_cache})
	app.run(host='0.0.0.0', port=80)
