#!/usr/bin/env bash

# usage: source ./test.sh

HOST=http://localhost
CARD_TOKEN=`curl $HOST/scripts/tokenization/tokens  \
  -H "Content-Type: application/json" \
  -d '{
     "number":"4030000010001234",
     "expiry_month":"02",
     "expiry_year":"20",
     "cvd":"123"
  }' | jq -r '.token'`

PROFILE_TOKEN=`curl $HOST/v1/profiles  \
  -H "Authorization: Passcode your_encoded_payment_profile_passcode"  \
  -H "Content-Type: application/json" \
  -d '{
      "token":{
        "name":"John Doe",
        "code":"'$CARD_TOKEN'"
      }
  }' | jq -r '.customer_code'`

curl $HOST/v1/payments  \
  -H "Authorization: Passcode your_encoded_payment_passcode"  \
  -H "Content-Type: application/json" \
  -d '{
     "amount":100.00,
     "payment_method":"payment_profile",
     "payment_profile":{
       "customer_code":"'$PROFILE_TOKEN'",
       "card_id":1,
       "complete":"true"
     }
  }' | jq