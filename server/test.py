import os
import datetime as dt
from unittest.mock import Mock
import time

import app
import database
import queries

def get_offers():

    return [
        {'coordinates': None,
        'utc_datetime': dt.datetime(2020, 1, 1, 1, 1, 1).strftime('%Y-%m-%d %H:%M:%S'),
        'id': 1,
        'name': '1',
        'price': 9.99,
        'classification': 'classification_1',
        'classification_description': '<h>description</h>',
        'classification_cover_image': '/image.png',
        'classification_images': '/image.png;/image.jpeg'},
        {'coordinates': None,
        'utc_datetime': dt.datetime(2023, 4, 10, 10, 30, 50).strftime('%Y-%m-%d %H:%M:%S'),
        'id': 2,
        'name': '2',
        'price': 9.99,
        'classification': 'classification_1',
        'classification_description': '<h>description</h>',
        'classification_cover_image': '/image.png',
        'classification_images': '/image.png;/image.jpeg'},
        {'coordinates': None,
        'utc_datetime': dt.datetime(2023, 4, 10, 10, 30, 50).strftime('%Y-%m-%d %H:%M:%S'),
        'id': 3,
        'name': '3',
        'price': 9.99,
        'classification': 'classification_2',
        'classification_description': '<h>description</h>',
        'classification_cover_image': '/image.png',
        'classification_images': '/image.png;/image.jpeg'},
        {'coordinates': None,
        'utc_datetime': dt.datetime(2023, 4, 10, 10, 30, 50).strftime('%Y-%m-%d %H:%M:%S'),
        'id': 4,
        'name': '4',
        'price': 10.99,
        'classification': 'classification_1',
        'classification_description': '<h>description</h>',
        'classification_cover_image': '/image.png',
        'classification_images': '/image.png;/image.jpeg'}
    ]

def get_orders():

    return [
        {'coordinates': None,
        'utc_datetime': dt.datetime(2023, 5, 20, 20, 40, 55).strftime('%Y-%m-%d %H:%M:%S'),
        'id': 1,
        'stripe_checkout_session_id': 111,
        'cache_stripe_payment_status': 'paid',
        'offer_id': 1,
        'courier_delivery_id': None,
        'cache_delivery_status': None}
    ]

def get_database(offers, orders):

    connection = database.get_connection(app.config['DATABASE_FILENAME'])

    connection.execute(queries.create_offers)

    if offers is not None:

        connection.executemany(queries.insert_offer, offers)

    connection.execute(queries.create_view_offering)

    connection.execute(queries.create_orders)

    if orders is not None:

        connection.executemany(queries.insert_order, orders)

    connection.commit()

    connection.close()

def test_get_offering_offers(classification, expected_offering, offers=None, orders=None):

    get_database(offers=offers, orders=orders)

    offering = app.get_offering_offers(classification=classification)

    os.remove(app.config['DATABASE_FILENAME'])

    assert offering == expected_offering

def test_get_offering_classifications(classification, expected_classifications, offers=None, orders=None):

    get_database(offers=offers, orders=orders)

    classifications = app.get_offering_classifications(classification=classification)

    os.remove(app.config['DATABASE_FILENAME'])

    assert classifications == expected_classifications

def test_get_checkout(request, expected_response, offers=None, orders=None):

    get_database(offers=offers, orders=orders)

    app.request = Mock()

    app.request.get_json.return_value = request

    response = app.get_checkout()

    os.remove(app.config['DATABASE_FILENAME'])

    assert response == expected_response

def test_select_offering_offer_of_id(id, expected_offer, offers=None, orders=None):

    get_database(offers=offers, orders=orders)

    connection = database.get_connection(app.config['DATABASE_FILENAME'])

    offer = dict(connection.execute(queries.select_offering_offer_of_id, (id,)).fetchone())

    connection.close()

    os.remove(app.config['DATABASE_FILENAME'])

    assert offer == expected_offer

def test_get_event(event, expected_response, offers=None, orders=None, session=None, expected_session_orders=None):

    get_database(offers=offers, orders=orders)

    app.request = Mock()

    app.request.headers.get.return_value = 'valid-stripe-signature'

    app.stripe = Mock()

    app.stripe.Webhook.construct_event.return_value = event

    if session is not None:

        app.stripe.checkout.Session.retrieve.return_value = session

    app.dt = Mock()

    app.dt.datetime.utcnow.return_value = dt.datetime(2023, 4, 30, 10, 5, 40)

    app.stripe.Product.retrieve.return_value = {'metadata': {
                                                    'id': 1
                                                }}

    response = app.get_event()

    assert response == expected_response

    if expected_session_orders is not None:

        connection = database.get_connection(app.config['DATABASE_FILENAME'])

        session_orders = [dict(row) for row in connection.execute(queries.select_orders_of_stripe_checkout_session_id, (session['id'],))]

        connection.commit()

        connection.close()

        assert session_orders == expected_session_orders

    os.remove(app.config['DATABASE_FILENAME'])

if __name__ == "__main__":

    begin = time.time()

    app.config = {'DATABASE_FILENAME': 'test.db', 'STRIPE_WEBHOOK_SECRET_KEY': 'valid-secret-key'}

    # no offers; no classification; empty list
    test_get_offering_offers(classification=None, expected_offering=[])

    # 4 offers; no classification; 3 offering (1 not latest datetime)
    test_get_offering_offers(offers=get_offers(), classification=None, expected_offering=[
        {'classification': 'classification_1',
        'classification_cover_image': '/image.png',
        'classification_description': '<h>description</h>',
        'classification_images': ['/image.png', '/image.jpeg'],
        'id': 2,
        'name': '2',
        'price': 9.99},
        {'classification': 'classification_2',
        'classification_cover_image': '/image.png',
        'classification_description': '<h>description</h>',
        'classification_images': ['/image.png', '/image.jpeg'],
        'id': 3,
        'name': '3',
        'price': 9.99},
        {'classification': 'classification_1',
        'classification_cover_image': '/image.png',
        'classification_description': '<h>description</h>',
        'classification_images': ['/image.png', '/image.jpeg'],
        'id': 4,
        'name': '4',
        'price': 10.99}
    ])

    # 4 offers; classification_1; 2 offering (1 not latest datetime, 1 not classification_1)
    test_get_offering_offers(offers=get_offers(), classification='classification_1', expected_offering=[
        {'classification': 'classification_1',
        'classification_cover_image': '/image.png',
        'classification_description': '<h>description</h>',
        'classification_images': ['/image.png', '/image.jpeg'],
        'id': 2,
        'name': '2',
        'price': 9.99},
        {'classification': 'classification_1',
        'classification_cover_image': '/image.png',
        'classification_description': '<h>description</h>',
        'classification_images': ['/image.png', '/image.jpeg'],
        'id': 4,
        'name': '4',
        'price': 10.99}
    ])

    # 4 offers; unclassified; empty list (no classification match)
    test_get_offering_offers(offers=get_offers(), classification='unclassified', expected_offering=[])

    test_get_offering_classifications(classification=None, expected_classifications=[])

    test_get_offering_classifications(offers=get_offers(), classification=None, expected_classifications=[{'classification': 'classification_1',
        'classification_cover_image': '/image.png',
        'classification_description': '<h>description</h>',
        'classification_images': ['/image.png', '/image.jpeg']},
        {'classification': 'classification_2',
        'classification_cover_image': '/image.png',
        'classification_description': '<h>description</h>',
        'classification_images': ['/image.png', '/image.jpeg']}
    ])

    test_get_offering_classifications(offers=get_offers(), classification='classification_1', expected_classifications=[{'classification': 'classification_1',
        'classification_cover_image': '/image.png',
        'classification_description': '<h>description</h>',
        'classification_images': ['/image.png', '/image.jpeg']}
    ])

    test_get_offering_classifications(classification='unclassified', expected_classifications=[])

    test_get_checkout(request='non-array', expected_response=('You did not POST an array of offer(s) to purchase in the POST body JSON; this is required.', 400))

    test_get_checkout(request=[], expected_response=('You did not POST at least one offer to purchase in the POST body JSON array; this is required.', 400))

    test_get_checkout(request=[{str(x): x} for x in range(101)], expected_response=('You attempted to purchase more than 100 items in one session; you may not purchase more than 100 items in one session.', 400))

    test_get_checkout(request=[{'no_id': 'no_id'}], expected_response=("You did not POST an id key in the {'no_id': 'no_id'} offer; this is required.", 400))

    test_get_checkout(offers=get_offers(), request=[{'id': 1}], expected_response=("You did not POST a valid id value in the {'id': 1} offer; this is required.", 400))

    test_select_offering_offer_of_id(offers=get_offers(), id='2', expected_offer={
        'id': 2, 
        'name': '2', 
        'price': 9.99, 
        'classification': 'classification_1'
    })

    test_get_event(event={
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 111
                }
            }
        },
        expected_response=('The checkout.session.completed event is acknowledged as a duplicate; no database insert.', 200),
        offers=get_offers(),
        orders=get_orders())

    test_get_event(event={
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 222
                }
            }
        },
        expected_response=(f'The stripe event is acknowledged.', 200),
        offers=get_offers(),
        orders=get_orders(),
        session={'id': '222',
                'payment_status': 'paid',
                'line_items': {
                    'data': [
                        {'price': {
                            'product': 1
                            }
                        },
                        {'price': {
                            'product': 1
                            }
                        }
                    ]
                }
            },
        expected_session_orders = [
            {'coordinates': None,
            'utc_datetime': dt.datetime(2023, 4, 30, 10, 5, 40).strftime('%Y-%m-%d %H:%M:%S'),
            'id': 2,
            'stripe_checkout_session_id': '222',
            'cache_stripe_payment_status': 'paid',
            'offer_id': 1,
            'courier_delivery_id': None,
            'cache_delivery_status': None},
            {'coordinates': None,
            'utc_datetime': dt.datetime(2023, 4, 30, 10, 5, 40).strftime('%Y-%m-%d %H:%M:%S'),
            'id': 3,
            'stripe_checkout_session_id': '222',
            'cache_stripe_payment_status': 'paid',
            'offer_id': 1,
            'courier_delivery_id': None,
            'cache_delivery_status': None}
        ]
    )

    end = time.time()

    elapsed = end - begin

    print(f'Tests passed in {elapsed:.2f} seconds.')




