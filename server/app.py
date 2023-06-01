from flask import Flask, request
from waitress import serve
import stripe
import json
import datetime as dt

import administrate
import database
import queries

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
        
        purchases = request.get_json()
    
    except:

        return 'You did not POST a JSON body; this is required.', 400

    if not isinstance(purchases, list):

        return 'You did not POST an array of offer(s) to purchase in the POST body JSON; this is required.', 400

    if not purchases:

        return 'You did not POST at least one offer to purchase in the POST body JSON array; this is required.', 400

    if len(purchases) > 100:

        return 'You attempted to purchase more than 100 items in one session; you may not purchase more than 100 items in one session.', 400

    line_items = []

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

    try:

        if config['SHIPPING'] is True:

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
                            'amount': config['SHIPPING_AMOUNT'],
                            'currency': 'USD'
                            }
                        }
                    }
                ]
            )

        else:

            checkout_session = stripe.checkout.Session.create(
                mode='payment',
                success_url=config['DOMAIN'] + '/complete',
                cancel_url=config['DOMAIN'] + '/cancel',
                line_items=line_items,
                automatic_tax={'enabled': True}
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

    config = administrate.get_config('config.json', ['DATABASE_FILENAME', 'OFFERING_FILENAME', 'ORDERS_UPDATE_FILENAME', 'DOMAIN', 'STRIPE_SECRET_KEY', 'STRIPE_WEBHOOK_SECRET_KEY', 'SHIPPING', 'SHIPPING_COUNTRIES', 'SHIPPING_AMOUNT'])

    stripe.api_key = config['STRIPE_SECRET_KEY']

    app = Flask(__name__)

    app.add_url_rule('/server/offering/offers', view_func=get_offering_offers, methods=['GET'])
    app.add_url_rule('/server/offering/offers/<classification>', view_func=get_offering_offers, methods=['GET'])

    app.add_url_rule('/server/offering/classifications', view_func=get_offering_classifications, methods=['GET'])
    app.add_url_rule('/server/offering/classifications/<classification>', view_func=get_offering_classifications, methods=['GET'])

    app.add_url_rule('/server/offering/purchases', view_func=get_checkout, methods=['POST'])

    app.add_url_rule('/server/events', view_func=get_event, methods=['POST'])

    serve(app, host='127.0.0.1', port=5000)
