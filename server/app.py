from flask import Flask, request
from waitress import serve
import stripe
import json
import datetime as dt
import requests

import administrate
import database
import queries
import ship

def get_offering_offers(classification=None):

    connection = database.get_connection(config['DATABASE_FILENAME'])

    if classification is None:

        matrix = [dict(row) for row in connection.execute(queries.select_offering_offers)]

        connection.close()

        return matrix

    else:

        matrix = [dict(row) for row in connection.execute(queries.select_offering_offers_of_classification, (classification,))]

        connection.close()

        return matrix

def get_offering_classifications(classification=None):

    connection = database.get_connection(config['DATABASE_FILENAME'])

    if classification is None:

        matrix = [dict(row) for row in connection.execute(queries.select_offering_classifications)]

        connection.close()

        return matrix

    else:

        matrix = [dict(row) for row in connection.execute(queries.select_offering_classification, (classification,))]

        connection.close()

        return matrix

def get_checkout():

    try:
        
        response = request.get_json()
    
    except:

        return 'You did not POST a JSON body; this is required.', 400

    if 'purchases' not in response:

        return 'You did not POST a purchases key in the POST body JSON; this is required.', 400

    purchases = response['purchases']

    if not isinstance(purchases, list):

        return 'You did not POST an array of offer(s) to purchase in the POST body JSON; this is required.', 400

    if not purchases:

        return 'You did not POST at least one offer to purchase in the POST body JSON array; this is required.', 400

    if len(purchases) > 100:

        return 'You attempted to purchase more than 100 items in one session; you may not purchase more than 100 items in one session.', 400

    line_items = []

    line_items_kilograms = 0.0

    for purchase in purchases:

        if 'id' not in purchase:

            return f'You did not POST an id key in the {str(purchase)} offer; this is required.', 400

        connection = database.get_connection(config['DATABASE_FILENAME'])

        if connection.execute(queries.offering_offer_exists, (purchase['id'],)).fetchone()[0] != 1:

            connection.close()

            return f'You did not POST a valid id value in the {str(purchase)} offer; this is required.', 400

        offer = connection.execute(queries.select_offering_offer_of_id, (purchase['id'],)).fetchone()

        connection.close()

        line_item = {
            'price_data': {
                'tax_behavior': 'exclusive',
                'currency': 'USD',
                'product_data': {
                    'name': str(offer['name']),
                    'metadata': {
                        'id': str(offer['id'])
                    },
                },
                'unit_amount': int(float(offer['price']) * 100)
            },
            'quantity': 1
        }

        line_items.append(line_item)

        line_items_kilograms = line_items_kilograms + float(offer['kilograms'])

    if 'postal_code' not in response:

        return 'You did not POST a postal_code key in the POST body JSON; this is required.', 400

    try:

        postal_code = str(response['postal_code']).strip()

    except:

        return 'The postal_code key in the POST body JSON could not be deserialized to type string; this is required.', 400

    if ship.is_text_length_digits(postal_code, 5) is False:

        return f'You POSTED the following postal_code: {postal_code}. It is not five digits. postal_code must be five digits.', 400

    line_items_ounces = line_items_kilograms * 35.274

    rate_response = requests.get(f'''
    https://secure.shippingapis.com/ShippingAPI.dll?API=RateV4
    &XML=<RateV4Request USERID="{config['USPS_USER_ID']}">
        <Revision>2</Revision>
        <Package ID="1">
            <Service>{config['USPS_SERVICE']}</Service>
            <ZipOrigination>{config['USPS_ORIGINATION_ZIP']}</ZipOrigination>
            <ZipDestination>{postal_code}</ZipDestination>
            <Pounds>0</Pounds>
            <Ounces>{line_items_ounces}</Ounces>
            <Container>{config['USPS_CONTAINER']}</Container>
        </Package>
    </RateV4Request>
    ''')

    if rate_response.status_code != 200:

        return 'The United States Postal Service Web Tools API is not available; it is required to calculate shipping rate. Therefore, your order cannot be completed at this time.', 400

    rate_text = rate_response.text

    if ship.get_xml_tag_content(rate_text, '<Error>', '</Error>') is not False:

        return f'The United States Postal Service Web Tools API responded with an error to our shipping rate request. Therefore, your order cannot be completed at this time.', 400

    rate = ship.get_xml_tag_content(rate_text, '<Rate>', '</Rate>')

    if rate is False:

        return f'The United States Postal Service Web Tools API did not respond with a valid shipping rate. Therefore, your order cannot be completed at this time.', 400

    try:

        checkout_session = stripe.checkout.Session.create(
            mode='payment',
            success_url=config['DOMAIN'] + '/complete',
            cancel_url=config['DOMAIN'] + '/cancel',
            line_items=line_items,
            automatic_tax={'enabled': True},
            shipping_address_collection={'allowed_countries': config['SHIPPING_COUNTRIES']},
            shipping_options=[
                {'shipping_rate_data': {
                    'tax_behavior': 'exclusive',
                    'display_name': 'Amount',
                    'type': 'fixed_amount',
                    'fixed_amount': {
                        'amount': int(float(rate)*100),
                        'currency': 'USD'
                        }
                    }
                }
            ]
        )             

    except:

        return f'The checkout session creation failed.', 500

    return {'url': checkout_session.url}

def get_event():

    stripe_signature = request.headers.get('stripe-signature')
    
    try:
        
        event = stripe.Webhook.construct_event(request.data, stripe_signature, config['STRIPE_WEBHOOK_SECRET_KEY'])
    
    except:
        
        return f'Stripe webhook validation failed.', 400

    if event['type'] == 'checkout.session.completed':

        connection = database.get_connection(config['DATABASE_FILENAME'])

        if connection.execute(queries.stripe_checkout_session_id_exists, (event['data']['object']['id'],)).fetchone()[0] != 0:

            return f'The checkout.session.completed event is acknowledged as a duplicate; no database insert.', 200

        connection.close()

        try:

            session = stripe.checkout.Session.retrieve(event['data']['object']['id'], expand=['line_items'])

        except:

            return f'Checkout session with line items could not be retrieved from Stripe; returning 400, therefore webhook retry.', 400

        orders = []

        utc_datetime = dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        for line_item in session['line_items']['data']:

            order = {}

            order['coordinates'] = None

            order['utc_datetime'] = utc_datetime

            order['id'] = None

            order['stripe_checkout_session_id'] = session['id']

            order['cache_stripe_payment_status'] = session['payment_status']

            try:

                product = stripe.Product.retrieve(line_item['price']['product'])

            except:

                return f'Product from checkout session line item could not be retrieved from Stripe; returning 400, therefore webhook retry.', 200

            order['offer_id'] = product['metadata']['id']

            order['courier_delivery_id'] = None

            order['cache_delivery_status'] = None

            orders.append(order)

        connection = database.get_connection(config['DATABASE_FILENAME'])

        connection.executemany(queries.insert_order, orders)

        connection.commit()

        connection.close()

    return f'The stripe event is acknowledged.', 200

if __name__ == "__main__":

    config = administrate.get_config('config.json', ['DATABASE_FILENAME', 'OFFERING_FILENAME', 'ORDERS_UPDATE_FILENAME', 'DOMAIN', 'STRIPE_SECRET_KEY', 'STRIPE_WEBHOOK_SECRET_KEY', 'SHIPPING_COUNTRIES', 'USPS_USER_ID', 'USPS_SERVICE', 'USPS_ORIGINATION_ZIP', 'USPS_CONTAINER'])

    stripe.api_key = config['STRIPE_SECRET_KEY']

    app = Flask(__name__)

    app.add_url_rule('/server/offering/offers', view_func=get_offering_offers, methods=['GET'])
    app.add_url_rule('/server/offering/offers/<classification>', view_func=get_offering_offers, methods=['GET'])

    app.add_url_rule('/server/offering/classifications', view_func=get_offering_classifications, methods=['GET'])
    app.add_url_rule('/server/offering/classifications/<classification>', view_func=get_offering_classifications, methods=['GET'])

    app.add_url_rule('/server/offering/purchases', view_func=get_checkout, methods=['POST'])

    app.add_url_rule('/server/events', view_func=get_event, methods=['POST'])

    serve(app, host='127.0.0.1', port=5000)
