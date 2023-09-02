import stripe
import os
import csv
import datetime as dt
import json

import database
import queries
import ship

def get_config(file, config_variables):

    with open(file, 'r') as config_json:

        config = json.load(config_json)

    for config_variable in config_variables:

        if config_variable not in config:

            raise Exception(f'{config_variable} configuration variable is not set in config.json; it must be set.')

    if 'USPS_ORIGINATION_ZIP' in config:

        if ship.is_text_length_digits(config['USPS_ORIGINATION_ZIP'], 5) is False:

            raise Exception('The USPS_ORIGINATION_ZIP config variable is not five digits; it must be five digits.')

    return config

def get_matrix(file):

    with open(file, mode='r') as matrix:

        return list(csv.DictReader(matrix))

def get_column(matrix, column_name, value):

    for i, row in enumerate(matrix):

        row[column_name] = value

if __name__ == "__main__":

    config = get_config('config.json', ['DATABASE_FILENAME', 'OFFERING_FILENAME', 'ORDERS_UPDATE_FILENAME', 'DOMAIN', 'STRIPE_SECRET_KEY', 'STRIPE_WEBHOOK_SECRET_KEY', 'SHIPPING_COUNTRIES', 'USPS_USER_ID', 'USPS_SERVICE', 'USPS_ORIGINATION_ZIP', 'USPS_CONTAINER'])

    connection = database.get_connection(config['DATABASE_FILENAME'])

    connection.execute(queries.create_offers)

    offering = get_matrix(config['OFFERING_FILENAME'])

    for column in ['kilograms', 'metres1', 'metres2', 'metres3']:

        for row in offering:

            try:

                value = float(row[column])

            except:

                exception = f'{column} of {row[column]} of row {row} cannot be converted to float; this is required.'

                raise Exception(exception)

            if value <= 0.0:

                exception = f'{column} of {value} of row {row} is not greater than 0; it must be greater than 0.'

                raise Exception(exception)

    get_column(matrix=offering, column_name='utc_datetime', value=dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))

    get_column(matrix=offering, column_name='coordinates', value=None)

    get_column(matrix=offering, column_name='id', value=None)

    connection.executemany(queries.insert_offer, offering)

    connection.execute(queries.create_view_offering)

    connection.execute(queries.create_orders)

    connection.commit()

    if os.path.isfile(config['ORDERS_UPDATE_FILENAME']):

        orders_update = get_matrix(config['ORDERS_UPDATE_FILENAME'])

        if len(orders_update) > 0:

            for row in orders_update:
                
                if set(row.keys()) != {'id', 'courier_delivery_id', 'cache_delivery_status'}:

                    exception = f'The fields in row {row} from {config["ORDERS_UPDATE_FILENAME"]} are not strictly id, courier_delivery_id, cache_delivery_status; the fields must strictly be id, courier_delivery_id, cache_delivery_status. The orders table was not updated. The orders-undelivered.csv file was not updated.'

                    raise Exception(exception)

                if connection.execute(queries.order_id_exists, (row['id'],)).fetchone()[0] == 0:

                    exception = f'id value of {row["id"]} in row {row} from {config["ORDERS_UPDATE_FILENAME"]} does not exist in the orders table; it must exist. The orders table was not updated. The orders-undelivered.csv file was not updated.'

                    raise Exception(exception)
                
            connection.executemany(queries.update_order, orders_update)

            connection.commit()

    undelivered_orders = [dict(row) for row in connection.execute(queries.select_not_delivered_orders)]

    connection.close()

    if len(undelivered_orders) > 0:

        stripe.api_key = config['STRIPE_SECRET_KEY']

        for undelivered_order in undelivered_orders:

            if undelivered_order['cache_stripe_payment_status'] == 'paid':

                session = stripe.checkout.Session.retrieve(undelivered_order['stripe_checkout_session_id'])

                undelivered_order['cache_stripe_payment_intent'] = session['payment_intent']

    with open('orders-undelivered.csv', mode='w+') as undelivered_orders_csv:

        csv_writer = csv.DictWriter(undelivered_orders_csv, fieldnames=['utc_datetime', 'id', 'stripe_checkout_session_id', 'cache_stripe_payment_status', 'offer_id', 'kilograms', 'metres1', 'metres2', 'metres3', 'name', 'courier_delivery_id', 'cache_delivery_status', 'cache_stripe_payment_intent'])

        csv_writer.writeheader()

        for undelivered_order in undelivered_orders:

            csv_writer.writerow(undelivered_order)

