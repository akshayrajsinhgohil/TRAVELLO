# Travello

A travel discovery and booking platform built with Django 5. Travellers browse
destinations, filter trips by budget and dates, book with live price
calculation, pay, and review. Staff get a customised admin plus an analytics
dashboard.

The whole thing runs on SQLite with a simulated payment gateway out of the box,
so you can clone it and have a working site in about ninety seconds — no
Postgres, no Razorpay account, no API keys.

---

## Quick start

```bash
git clone <your-repo-url> travello
cd travello

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env               # the defaults work as-is for development

python manage.py migrate
python manage.py seed_data         # 12 destinations, 13 trips, demo bookings
python manage.py runserver
```

Open <http://127.0.0.1:8000>.

| What | Where | Login |
| --- | --- | --- |
| Public site | `/` | — |
| Traveller dashboard | `/accounts/me/` | `demo` / `travello123` |
| Staff analytics | `/staff/` | `admin` / `travello123` |
| Django admin | `/admin/` | `admin` / `travello123` |

Try the discount code **`FIRSTTRIP`** at checkout (15% off, capped at ₹5,000).

> **Change the demo passwords before this touches a real server.** They exist so
> the project is explorable on first run, nothing more.

---

## What's in the box

### For travellers

- **Animated landing page** — a Three.js wireframe globe with live destination
  pins and flight arcs, GSAP hero timeline, scroll reveals, count-up statistics,
  and a testimonial wall.
- **Accounts** — registration with emailed verification links, sign in with
  *either* username or email, password reset, editable profile with avatar.
- **Browse and search** — free-text search across trip titles, descriptions,
  destinations and categories, plus filters for destination, travel style,
  price range, departure date and group size, with five sort orders. Filters
  survive pagination.
- **Trip pages** — photo gallery, day-by-day itinerary timeline, inclusions and
  exclusions, rating breakdown, reviews, and a sticky booking panel.
- **Booking** — date picker, guest counts, discount codes, and a price summary
  that recalculates over fetch as you change anything.
- **Payment** — a three-step checkout ending in a confirmation page and an
  emailed receipt.
- **Dashboard** — booking history split into upcoming and past, total spend,
  countries visited, saved trips and your own reviews.
- **Wishlist** — a heart button on every trip card that saves without a page
  reload.
- **Reviews** — one per traveller per trip, held for moderation, badged as
  "verified" when linked to a paid booking.

### For staff

- **Customised Django admin** — Travello-tinted, with image thumbnails, inline
  editing of galleries and itinerary days directly on the trip form, prepopulated
  slugs, and bulk actions (publish, feature, confirm bookings, approve reviews).
- **Analytics dashboard** at `/staff/` — revenue and booking KPIs, a trailing
  twelve-month combo chart, status doughnut, revenue by destination, plus a
  "needs attention" panel for unapproved reviews, unanswered messages, unpaid
  bookings and departures inside seven days. Drawn with Chart.js.

---

## Architecture

```
config/          settings, root URLconf, WSGI/ASGI
apps/
  accounts/      custom User model, auth backend, wishlist, profile
  destinations/  categories, destinations, trip packages, itineraries, DRF API
  bookings/      bookings, coupons, payments, gateway adapters
  reviews/       traveller reviews and moderation
  core/          marketing pages, testimonials, newsletter, contact, seeder
  dashboard/     staff analytics (no models of its own)
templates/       all HTML, organised by app
static/          travello.css, travello.js, globe.js
fixtures/        sample_data.json — the catalogue, for loaddata
```

Apps live under `apps/` with explicit labels, so `INSTALLED_APPS` reads
`apps.bookings.apps.BookingsConfig` while the app label stays `bookings`.

### Decisions worth knowing about

**A custom user model from day one.** Swapping `AUTH_USER_MODEL` later is one of
the genuinely painful Django migrations, so `accounts.User` exists from the
first migration even though it started as a thin subclass.

**Pricing lives in one method.** `Package.quote(guests, coupon)` returns every
line the checkout shows — unit price, subtotal, discount, tax, total. The
checkout view, the live-quote endpoint and the seeder all call it, so the number
on the summary panel is arithmetically the same one that gets stored on the
booking. Tax rate comes from `TAX_PERCENT`.

**Payments go through an adapter.** `bookings/gateways.py` defines a three-method
interface with three implementations. `SandboxGateway` is the default: it
simulates a successful payment, never touches the network, and needs no
credentials. Point `PAYMENT_GATEWAY` at `razorpay` or `stripe` and add keys to
switch. If the SDK or the keys are missing the code falls back to sandbox rather
than crashing, which keeps a misconfigured deploy browsable.

**Images have a remote fallback.** Every catalogue model mixes in
`ImageFallbackMixin`, which pairs an uploaded `image` with an `image_url` string
and exposes `display_image`. Uploads always win. This is why the repo ships no
binaries and the seeder needs no network access.

**Seed photos are placeholders.** They come from `picsum.photos` with a fixed
per-slug seed, so the demo looks identical on every machine and nothing 404s —
but the photo of "Bali" is not actually Bali. Drag real photography onto any
record in the admin and it takes over immediately.

**Reviews are moderated by default.** `is_approved` starts `False`, and every
rating aggregate filters on it, so a new review cannot move a trip's average
before a human has looked at it.

---

## Configuration

Everything is read from `.env` via `python-decouple`. `.env.example` documents
every key; the ones that matter most:

| Variable | Default | Notes |
| --- | --- | --- |
| `SECRET_KEY` | — | Generate a real one for anything public. |
| `DEBUG` | `True` | Set `False` in production — it switches on HSTS, secure cookies and SSL redirect. |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated. |
| `DATABASE_URL` | unset | Unset means SQLite. Set a `postgres://` URL to switch. |
| `PAYMENT_GATEWAY` | `sandbox` | `sandbox`, `razorpay` or `stripe`. |
| `TAX_PERCENT` | `5` | Applied after any discount. |
| `EMAIL_HOST` | blank | Blank prints emails to the console — verification links included. |
| `USE_CLOUDINARY` | `False` | `True` pushes uploads to Cloudinary instead of disk. |

### Switching to PostgreSQL

```bash
# .env
DATABASE_URL=postgres://travello:password@localhost:5432/travello
```

Then `python manage.py migrate`. Nothing else changes — `dj-database-url` reads
the URL and `psycopg` is already in `requirements.txt`.

### Turning on a real payment gateway

```bash
# .env
PAYMENT_GATEWAY=razorpay
RAZORPAY_KEY_ID=rzp_test_xxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxx
```

The pay page swaps the sandbox button for Razorpay's checkout modal on its own.
Stripe works the same way with `STRIPE_PUBLIC_KEY` and `STRIPE_SECRET_KEY`.

---

## Sample data

Two ways to load the catalogue, both idempotent:

```bash
python manage.py seed_data                    # add or update demo content
python manage.py seed_data --fresh            # wipe the catalogue first
python manage.py seed_data --no-demo-bookings # catalogue only, no fake history

python manage.py loaddata fixtures/sample_data.json   # catalogue only
```

`seed_data` is the fuller option: alongside the 12 destinations and 13 trips it
creates users, 56 bookings back-dated across twelve months, and reviews — which
is what gives the analytics dashboard something to draw. The randomness is
seeded, so every machine gets the same numbers.

`loaddata` gives you just the catalogue: destinations, trips, itineraries,
galleries, testimonials and coupons.

---

## Tests

```bash
python manage.py test                  # 135 tests
python manage.py test apps.bookings    # one app
```

Coverage is aimed at the paths where a bug costs money or lets someone see
another person's data:

- **`apps/bookings`** — price arithmetic (discounts, percentage caps, flat codes
  larger than the basket, expired and exhausted coupons), the full checkout
  flow, payment callbacks in both directions, cancellation and refund marking,
  and a block of ownership tests asserting one traveller gets a 404 rather than
  another's booking.
- **`apps/accounts`** — registration, duplicate-email rejection, verification
  token validity and replay, login by username *and* email, wishlist toggling,
  profile updates.
- **`apps/destinations`** — every filter and sort order, moderation-gated rating
  aggregates, slug generation, and a guard that runs `seed_data` and checks that
  every seeded record produces a URL that resolves.
- **`apps/reviews`** — the moderation gate, one-review-per-trip, verified
  badging, and deletion permissions.
- **`apps/core`** — marketing pages, newsletter, contact form, and the staff
  dashboard's access control and chart payloads.

Shared builders live in `apps/core/test_factories.py`.

---

## Deployment

### Render

`render.yaml` is a working blueprint: push the repo, point Render at it, and it
provisions a Postgres instance and a web service. Set `SITE_URL`, `SITE_DOMAIN`
and `CSRF_TRUSTED_ORIGINS` to your actual URL once the service has a hostname.

To load demo content on the first deploy only, set `SEED_DEMO_DATA=True`, deploy,
then delete the variable.

### Anything else

`Procfile` and `build.sh` work on Railway, Fly, Heroku or a plain container.
Manually:

```bash
export DEBUG=False
export SECRET_KEY="…"
export DATABASE_URL="postgres://…"
export ALLOWED_HOSTS="travello.example.com"

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

Static files are served by WhiteNoise, so no separate Nginx `location` block is
needed — though putting Nginx in front for TLS and buffering is still sensible.

### Before going live

- [ ] New `SECRET_KEY`, `DEBUG=False`, real `ALLOWED_HOSTS`
- [ ] Change or delete the `admin` and `demo` accounts
- [ ] Real SMTP credentials, or verification emails go nowhere
- [ ] Real gateway keys if you intend to take money
- [ ] Compile Tailwind properly (see below)
- [ ] Point `SITE_URL` and `SITE_DOMAIN` at the real domain — emails, canonical
      tags and the sitemap all read them

---

## The Tailwind situation

Templates load Tailwind from the Play CDN with an inline `tailwind.config` that
defines the Travello palette. That's deliberate for a project meant to run
immediately after clone, but the CDN build compiles in the browser on every page
load and ships every utility class. **Don't leave it that way in production.**

```bash
npm install -D tailwindcss
npx tailwindcss init
# content: ["./templates/**/*.html", "./apps/**/*.py"]
npx tailwindcss -i ./static/css/input.css -o ./static/css/tailwind.css --minify
```

Then swap the CDN `<script>` in `templates/base.html` for the compiled
stylesheet. The custom palette and font stack already live in
`static/css/travello.css` as CSS variables, so they carry over unchanged.

---

## Design notes

The palette is "dusk from a plane window" — deep indigo grounds
(`#0E0A1F`, `#150E2B`, `#1D1438`), cream text, with magenta → violet → amber
gradients for accents and mint reserved for prices and confirmations, so money
always reads the same way. Display type is Bricolage Grotesque, body is Plus
Jakarta Sans.

Everything animated sits behind `prefers-reduced-motion`, including the globe,
which skips its render loop entirely rather than just slowing down. The design
tokens are CSS custom properties in `static/css/travello.css`, so retheming is
a matter of editing nine variables.

---

## Licence

MIT. The photographs are placeholders from picsum.photos; replace them with
images you have the rights to before launch.
