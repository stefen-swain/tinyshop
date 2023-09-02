import stripe
import csv
import requests

import administrate

def get_xml_tag_content(xml, start_tag, end_tag):

    if start_tag in xml:

        xml_post_start_tag = xml.split(start_tag)[1]

        if end_tag in xml_post_start_tag:

            content = xml_post_start_tag.split(end_tag)[0]

            return content

        else:

            return False

    else:

        return False

def is_text_length_digits(text, length):

    if (len(text) == length) and (text.isdigit()):

        return True

    else:

        return False


def get_manifest(undelivered_orders):

    packages = []

    for undelivered_order in undelivered_orders:

        package = {
            'stripe_checkout_session_id': undelivered_order['stripe_checkout_session_id']
        }

        if package not in packages:

            packages.append(package)

    for package in packages:

        session = stripe.checkout.Session.retrieve(package['stripe_checkout_session_id'])

        verify_address_response = requests.get(f'''
        https://secure.shippingapis.com/ShippingAPI.dll?API=Verify&XML=<AddressValidateRequest USERID="{config['USPS_USER_ID']}">
            <Revision>1</Revision>
            <Address>
                <Address1>{session['shipping_details']['address']['line2']}</Address1>
                <Address2>{session['shipping_details']['address']['line1']}</Address2>
                <City>{session['shipping_details']['address']['city']}</City>
                <State>{session['shipping_details']['address']['state']}</State>
                <Zip5>{session['shipping_details']['address']['postal_code']}</Zip5>
                <Zip4></Zip4>
            </Address>
        </AddressValidateRequest>
        ''')

        if verify_address_response.status_code != 200:

            raise Exception('The United States Postal Service Web Tools API is not available; it is required to verify shipping addresses. Therefore, order shipping cannot be completed at this time.')

        verify_address_text = verify_address_response.text

        error = get_xml_tag_content(verify_address_text, '<Error>', '</Error>')

        if error is not False:

            exception = f'The United States Postal Service Web Tools API responded with the following error to our address verification request: {error}.'

            raise Exception(exception)

        verify_address = get_xml_tag_content(verify_address_text, '<DPVConfirmation>', '</DPVConfirmation>')

        if verify_address is False:

            exception = f'The United States Postal Service Web Tools API did not respond with a valid address verification: {verify_address_text}.'

            raise Exception(exception)

        if verify_address == 'N':

            exception = f'''The United States Postal Service Web Tools API declares address {session['shipping_details']['address']} for checkout session {undelivered_order['stripe_checkout_session_id']} undeliverable. Manually process the shipping or cancellation of the associated order(s), update order(s) status in orders-update.csv, execute administrate.py, and re-execute ship.py.'''

            raise Exception(exception)

        package['name'] = session['shipping_details']['name']
        
        package['line1'] = session['shipping_details']['address']['line1']

        package['line2'] = session['shipping_details']['address']['line2']

        package['city'] = session['shipping_details']['address']['city']

        package['state'] = session['shipping_details']['address']['state']

        package['postal_code'] = session['shipping_details']['address']['postal_code']

        package['country'] = session['shipping_details']['address']['country']

        package['orders'] = []

        package['kilograms'] = 0.0

        package['metres1'] = 0.0

        package['metres2'] = 0.0

        package['metres3'] = 0.0

        for undelivered_order in undelivered_orders:
            
            if undelivered_order['stripe_checkout_session_id'] == package['stripe_checkout_session_id']:

                package['orders'].append(int(undelivered_order['id']))

                package['kilograms'] = package['kilograms'] + float(undelivered_order['kilograms'])

                undelivered_order['dimensions'] = sorted([float(undelivered_order['metres1']), float(undelivered_order['metres2']), float(undelivered_order['metres3'])])

                if undelivered_order['dimensions'][-1] > package['metres1']:

                    package['metres1'] = undelivered_order['dimensions'][-1]

                if undelivered_order['dimensions'][-2] > package['metres2']:

                    package['metres2'] = undelivered_order['dimensions'][-2]

                package['metres3'] = package['metres3'] + undelivered_order['dimensions'][-3]

        package['ounces'] = package['kilograms'] * 35.274

        for i, inches_dimension in enumerate(['inches1', 'inches2', 'inches3']):

            metres_dimension = 'metres' + str(i+1)

            package[inches_dimension] = package[metres_dimension] * 39.3701

    return packages

if __name__ == "__main__":

    config = administrate.get_config('config.json', ['DATABASE_FILENAME', 'OFFERING_FILENAME', 'ORDERS_UPDATE_FILENAME', 'DOMAIN', 'STRIPE_SECRET_KEY', 'STRIPE_WEBHOOK_SECRET_KEY', 'SHIPPING_COUNTRIES', 'USPS_USER_ID', 'USPS_SERVICE', 'USPS_ORIGINATION_ZIP', 'USPS_CONTAINER'])

    stripe.api_key = config['STRIPE_SECRET_KEY']

    packages = get_manifest(administrate.get_matrix('orders-undelivered.csv'))
        
    with open('ship-orders-undelivered.csv', mode='w+') as ship_undelivered_orders_csv:

        csv_writer = csv.DictWriter(ship_undelivered_orders_csv, fieldnames=['stripe_checkout_session_id', 'name', 'line1', 'line2', 'city', 'state', 'postal_code', 'country', 'orders', 'kilograms', 'metres1', 'metres2', 'metres3', 'ounces', 'inches1', 'inches2', 'inches3'])

        csv_writer.writeheader()

        for package in packages:

            csv_writer.writerow(package)