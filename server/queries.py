wal = '''
pragma journal_mode = WAL;
'''

create_offers = '''
CREATE TABLE IF NOT EXISTS offers
(
coordinates TEXT,
utc_datetime TEXT,
id INTEGER PRIMARY KEY AUTOINCREMENT,
kilograms REAL,
metres1 REAL,
metres2 REAL,
metres3 REAL,
name TEXT,
price REAL,
classification TEXT,
classification_description TEXT,
classification_cover_image TEXT,
classification_images TEXT
)
'''

insert_offer = '''
INSERT INTO offers VALUES(:coordinates, :utc_datetime, :id, :kilograms, :metres1, :metres2, :metres3, :name, :price, :classification, :classification_description, :classification_cover_image, :classification_images)
'''

create_view_offering = '''
/* This view returns the offering. */
CREATE VIEW IF NOT EXISTS offering AS
SELECT * FROM offers
WHERE utc_datetime = (SELECT MAX(utc_datetime) FROM offers)
'''

select_offering_offers = '''
SELECT id, name, price, classification, classification_description, classification_cover_image, classification_images AS "classification_images [list]" FROM offering
ORDER BY id
'''

select_offering_offers_of_classification = '''
SELECT id, name, price, classification, classification_description, classification_cover_image, classification_images AS "classification_images [list]" FROM offering
WHERE classification = ?
ORDER BY id
'''

select_offering_classifications = '''
SELECT classification, classification_description, classification_cover_image, classification_images AS "classification_images [list]" FROM offering
GROUP BY classification
ORDER BY id
'''

select_offering_classification = '''
SELECT classification, classification_description, classification_cover_image, classification_images AS "classification_images [list]" FROM offering
WHERE classification = ?
GROUP BY classification
ORDER BY id
'''

offering_offer_exists = '''
SELECT EXISTS 
(
SELECT * FROM offering
WHERE id = ?
)
'''

select_offering_offer_of_id = '''
SELECT id, kilograms, metres1, metres2, metres3, name, price, classification FROM offering
WHERE id = ?
LIMIT 1
'''

create_orders = '''
CREATE TABLE IF NOT EXISTS orders
(
coordinates TEXT,
utc_datetime TEXT,
id INTEGER PRIMARY KEY AUTOINCREMENT,
stripe_checkout_session_id TEXT,
cache_stripe_payment_status TEXT,
offer_id INTEGER,
courier_delivery_id TEXT,
cache_delivery_status TEXT,
FOREIGN KEY (offer_id) REFERENCES offers(id)
)
'''

stripe_checkout_session_id_exists = '''
SELECT EXISTS 
(
SELECT * FROM orders
WHERE stripe_checkout_session_id = ?
)
'''

order_id_exists = '''
SELECT EXISTS 
(
SELECT * FROM orders
WHERE id = ?
)
'''

select_orders_of_stripe_checkout_session_id = '''
SELECT * FROM orders
WHERE stripe_checkout_session_id = ?
'''

insert_order = '''
INSERT INTO orders VALUES(:coordinates, :utc_datetime, :id, :stripe_checkout_session_id, :cache_stripe_payment_status, :offer_id, :courier_delivery_id, :cache_delivery_status)
'''

update_order = '''
UPDATE orders
SET
id = :id,
courier_delivery_id = :courier_delivery_id,
cache_delivery_status = :cache_delivery_status
WHERE id = :id
'''

select_not_delivered_orders = '''
SELECT orders.utc_datetime, orders.id, stripe_checkout_session_id, cache_stripe_payment_status, offer_id, offers.kilograms, offers.metres1, offers.metres2, offers.metres3, offers.name, courier_delivery_id, cache_delivery_status FROM orders
LEFT JOIN offers ON orders.offer_id = offers.id
WHERE (cache_delivery_status IS NOT 'delivered') AND (cache_delivery_status IS NOT 'canceled')
'''
