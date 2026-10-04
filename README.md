# Wardrobe template: Backend

The API behind the clothing store website, the admin back office and the customer app: catalogue, colours and sizes, stock, bag pricing, orders, payments, shipping and returns.

Django 6.1 and Django REST Framework. Part of the [`templates-wardrobe`](https://github.com/mattoznav/templates-wardrobe) template, inside the [`templates`](https://github.com/mattoznav/templates) collection.

## Requirements

- Python 3.12 or newer (Django 6.1 needs it)
- Nothing else: no database server (the data are CSV files loaded into SQLite) and no payment account (a built-in fake provider simulates payments)

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python manage.py bootstrap
.venv/bin/python manage.py runserver 8001
```

The API is at `http://localhost:8001/api/` and the Django admin at `http://localhost:8001/admin/`.
The port is 8001 so the wardrobe can run next to the cinema template.
To get an admin user, set `DEMO_ADMIN_PASSWORD` in `.env` before running `bootstrap`, or run `manage.py createsuperuser`.

`bootstrap` also creates a month of fictional orders, payments and returns, so the back office has figures to show. Use `bootstrap --no-demo-orders` for an empty order book.

Run the tests with `.venv/bin/python manage.py test`.

## Data: CSV files instead of a database server

There is no database to install. The files in [`data/`](data) are the tables:

| File | Table |
| --- | --- |
| `store.csv` | The shop: name, address, opening hours, currency, free shipping amount, return window |
| `categories.csv`, `colours.csv`, `sizes.csv` | Reference data. Sizes come in three systems: letters, EU shoe sizes and one size |
| `products.csv` | The catalogue, with prices, old prices for items on sale, and "days since added" |
| `variants.csv` | One row per colour and size, with its SKU and stock |
| `photos.csv`, `product_images.csv` | Photos with their credits, and which product and colour they show |
| `collections.csv`, `collection_products.csv` | Curated edits and their products |
| `editorial.csv` | Copy and images for the home page, departments and story blocks |
| `shipping_methods.csv` | Standard, express, collect in store |

`manage.py bootstrap` creates a local SQLite file in `var/` (ignored by git) and fills it from the CSV files.
Orders, payments, returns and users live only in that file: run `manage.py bootstrap` again to reset the demo.

The CSV files are read, never written: stock reservations need transactions and constraints that plain files cannot give.
To go to production, set `DATABASE_URL` (for example `postgres://user:password@host:5432/wardrobe`): nothing else changes.

### Regenerating the data

```bash
python tools/build_catalog.py
```

The products, colours and stock levels are defined in that script. Stock comes from a fixed seed, so the output is always the same.

### Photos and licenses

- Product and editorial photos are from [Unsplash](https://unsplash.com) and are used under the [Unsplash License](https://unsplash.com/license). They are not copied into the repository: every client loads them from the Unsplash CDN (`images.unsplash.com`) and asks for the size it needs with the `w`, `h`, `fit` and `q` parameters.
- Each photo keeps its photographer and source page in `photos.csv`. The website and the app show the credit next to each image.
- The brand, the store, the products, their descriptions and every person in the demo orders are fictional.

## Orders and stock

1. `POST /api/bag/quote/` prices a bag with today's prices, stock and shipping. Nothing is reserved.
2. `POST /api/orders/` takes the pieces out of stock for 15 minutes (`ORDER_HOLD_MINUTES`) and returns a pending order.
3. `POST /api/orders/<id>/checkout/` creates a payment and returns the `client_secret`.
4. The client completes the payment; the provider reports the outcome to the backend and the order becomes paid.
5. Staff ship the order with a tracking number, then mark it delivered. Unpaid orders expire and their stock goes back.

Edge cases are handled on purpose:

- **No overselling.** Stock is taken with a conditional update (`stock >= quantity`), backed by a database constraint (`stock >= 0`). If one line of an order is short, the whole order is rolled back.
- **One unpaid order per customer.** Placing a new order cancels the previous unpaid one and returns its stock.
- **Late payments.** A payment that arrives after the hold expired is kept if the stock is still there, and refunded otherwise. Duplicate webhooks are ignored.
- **Cancellations.** Customers can cancel until the order ships; paid orders are refunded in full and restocked.

### Returns

Customers can return pieces of a shipped or delivered order within the return window (`return_window_days` in `store.csv`, 30 days by default).
Staff then either **receive** the parcel, which restocks the pieces and refunds their price (a partial refund, shipping is kept), or **reject** it with a note for the customer.

### Payment providers

| `PAYMENT_PROVIDER` | Use it for |
| --- | --- |
| `fake` (default) | Demos and development. No account, no keys, no money. The client "pays" with `POST /api/payments/fake/complete/` (`{"payment_id": 1, "outcome": "succeeded"}` or `"failed"`). |
| `stripe` | Real payments with [Payment Intents](https://docs.stripe.com/payments/payment-intents) and partial refunds. Selected automatically when `STRIPE_SECRET_KEY` is set. |

To try Stripe without moving money, use the test mode keys from the Stripe dashboard and the [test cards](https://docs.stripe.com/testing).
Locally, forward webhooks with the Stripe CLI:

```bash
stripe listen --forward-to localhost:8001/api/payments/stripe/webhook/
```

and put the `whsec_...` secret it prints in `STRIPE_WEBHOOK_SECRET`.

## API

Public reads, authenticated orders, staff-only writes. Authentication uses JWT: send `Authorization: Bearer <access token>`.

| Method | Path | Who | What |
| --- | --- | --- | --- |
| GET | `/api/store/`, `/api/editorial/` | anyone | Shop details; copy and images for the pages around the catalogue |
| GET | `/api/products/` | anyone | Filters (comma lists): `department`, `category`, `colour`, `size` (in stock), `collection`, `q`, `on_sale=1`, `new=1`, `in_stock=1`, `sort` (`featured`, `newest`, `price_asc`, `price_desc`) |
| GET | `/api/products/<slug>/` | anyone | One product with images, colours, sizes and live stock per variant |
| GET | `/api/categories/`, `/api/colours/`, `/api/sizes/`, `/api/collections/`, `/api/shipping-methods/` | anyone | Reference data |
| POST | `/api/bag/quote/` | anyone | `{"items": [{"variant": 1, "quantity": 2}], "shipping_method": "standard"}`: prices, shipping, total and problems such as "only 1 left" |
| POST | `/api/auth/register/` | anyone | Create an account, returns tokens |
| POST | `/api/auth/token/`, `/api/auth/token/refresh/` | anyone | Sign in, refresh |
| GET, PATCH | `/api/auth/me/` | user | Profile |
| GET, POST | `/api/orders/` | user | Own orders (staff: all, with customer and payments). Body: items, `shipping_method` and `address`. Staff filters: `q`, `status`, `date` |
| POST | `/api/orders/<id>/checkout/` | user | Start paying |
| POST | `/api/orders/<id>/cancel/` | user | Cancel before shipping, with a full refund if paid |
| POST | `/api/orders/<id>/ship/`, `/api/orders/<id>/deliver/` | staff | Fulfilment, with an optional `tracking_number` |
| GET, POST | `/api/returns/` | user | Own returns (staff: all). Body: `order`, `lines` (`order_line`, `quantity`), `reason`, `note` |
| POST | `/api/returns/<id>/receive/`, `/api/returns/<id>/reject/` | staff | Restock and refund, or reject with a `staff_note` |
| GET | `/api/inventory/` | staff | Every variant with its stock. Filters: `q`, `low=1`, `category` |
| POST | `/api/inventory/<id>/adjust/` | staff | `{"delta": 5}` or `{"delta": -2}`. Safe while orders come in |
| GET | `/api/admin/summary/` | staff | Sales by day (`days`, default 14), today, orders to ship, open returns, low stock, best sellers |
| POST, PUT, PATCH, DELETE | `/api/products/` | staff | Manage the catalogue, with `images` and `variants` in the same request. Ordered products cannot be deleted: archive them |
| GET | `/api/payments/config/` | anyone | Active provider and its public key |
| POST | `/api/payments/stripe/webhook/` | Stripe | Payment outcomes |

## Maintenance

`manage.py release_expired_orders` puts back the stock of unpaid orders. The API already does it when products and orders are read; schedule it with cron to keep stock exact between visits.
