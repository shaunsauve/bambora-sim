
**Bambora** is a payment gateway.  This is a little simulator of some of their endpoints for use in testing.  Note that they do already offer a sandbox for development, see [https://dev.na.bambora.com/docs/](https://dev.na.bambora.com/docs/)

# bootstrap

```bash
# python 3.7 has some nifty string features
sudo apt-get install python3.7 python3-pip
# install virtual environment + dependency manager 
sudo pip3 install pipenv
git clone <project>
cd project
# install dependencies
pipenv sync
```

# example interaction

create single use token

```bash
curl http://localhost/scripts/tokenization/tokens  \
	-H "Content-Type: application/json" \
	-d '{
            "number":"4030000010001234",
            "expiry_month":"02",
            "expiry_year":"20",
            "cvd":"123"
        }'

# output
{ 
    "code":1, 
    "message":"",
    "token":"C-3PhrFw-0001-28092019-0457-18799008-1234",
    "version":1
}
```

create profile/multi-use token from single use token

```bash
curl http://localhost/v1/profiles  \
	-H "Authorization: Passcode your_encoded_payment_profile_passcode"  \
	-H "Content-Type: application/json" \
	-d '{  
            "token":{
                "name":"John Doe",
                "code":"C-3PhrFw-0001-28092019-0457-18799008-1234"
            }
        }'

# output
{
    "code":1,
    "message":"",
    "token":"P-3PhrFw-0002-28092019-0457-41493767-1234",
    "version":1
}
```

perform payment using profile/multi-use token

```bash
curl http://localhost/v1/payments  \
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
        }'
```

SEE test.sh
