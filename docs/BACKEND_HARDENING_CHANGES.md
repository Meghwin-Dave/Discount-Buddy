# Backend Hardening & Performance Changes

Date: 2026-10-10

Five backend-only fixes that make the app faster and close two security holes, **without changing any API response the published app depends on** (same URLs, same JSON fields, same 4-digit OTP length).

| Change | Problem fixed | Result |
| --- | --- | --- |
| Home and restaurant list queries | One extra query per restaurant, whole catalogue loaded | `/home` 91 → 9 queries (guest), 103 → 17 (logged in); list 38 → 16 |
| Review ownership | Any customer could edit or delete anyone's review | Only the author can; others get 404 |
| Auth throttling and OTP limits | 4-digit codes could be guessed freely; no rate limits | 10 guesses per email per hour, per-IP limits on login and sign-up |
| Atomic deal claiming | Two simultaneous taps could exceed a deal's limits | Limits re-checked under a database lock |
| One database index | Latest mystery-visit lookup scanned more than needed | Added `mysteryvisit_latest_idx` |

All 73 tests pass, including 12 new ones in `restaurants/tests_hardening.py`. For the home and list endpoints the JSON output was compared before and after across 12 requests and is identical.

---

## 1. Why this was needed

- **Exploitable now:** any logged-in customer could change or delete any other user's review, and the 4-digit sign-up / reset codes (10,000 possibilities) could be guessed with no limit.
- **Slows down as you grow:** the home screen ran roughly 10 database queries per restaurant. With 500 restaurants that is about 5,000 queries for one screen load.
- **Wrong under load:** the check that stops a user claiming a deal too many times ran before the claim was saved, not during it. Two taps at the same moment could both pass.

The app needs no code change for any of these. It already displays the `detail` message of any error response, so the new rate-limit message appears as normal text.

---

## 2. Home and restaurant list speed

The home screen used to ask the database a fresh question for every restaurant it showed. It now loads everything it needs in a handful of batched queries and does the rest in memory. Output is unchanged.

### Before

- The restaurant list was fetched 4 separate times for the home sections (nearby, top 10, featured, all).
- Rating, review count, active-deal count and claim count came from joining four tables together, which multiplies rows before counting.
- For each restaurant the code then asked separate questions: its active deals, cuisines, primary image (up to 2 queries), whether the user saved it, its latest mystery visit, its average rating and its review count (the last two were asked even when the answer was already known).

### Now

- The list is fetched **once**; every section is sorted from it in Python.
- The four counters are small per-restaurant subqueries instead of one big join (`annotate_restaurant_stats` in `restaurants/views.py`).
- Active deals, images and cuisines are loaded for all restaurants together (`Prefetch`, `prefetch_active_deals`) and read from memory.
- The user's saved restaurants (`saved_restaurant_ids`) and each restaurant's latest mystery visit (`attach_latest_mystery_visits` in `restaurants/services.py`) are each loaded in **one** query.
- Ties between equal leaderboard scores are ordered by restaurant id, so the order is stable.

### Measured (8 restaurants)

| Request | Queries before | Queries after |
| --- | --- | --- |
| `/home` (guest) | 91 | 9 |
| `/home` (logged in) | 103 | 17 |
| `/restaurants` list (guest) | 38 | 16 |
| `/restaurants` list (logged in) | 46 | 17 |

The "before" cost grows with every restaurant added; the "after" cost stays flat (a test checks the count is identical with 3 vs 10 restaurants).

Note: the nearest-first sort still runs in Python after loading all restaurants. That is fine for hundreds. If the list grows into the thousands, filter by a bounding box in the database first.

---

## 3. Review ownership

Only the author of a review can now edit or delete it. Before, the server checked you were a logged-in customer but never that the review was yours.

| | Before | Now |
| --- | --- | --- |
| Author edits own review | Works | Works |
| Another customer edits or deletes it | Worked | 404 Not Found, review unchanged |
| Anyone reads reviews | Works | Works (still public) |

Ratings feed the restaurant leaderboard, so this hole let anyone change rankings or wipe a competitor's reviews. The app only edits the user's own reviews, so real users see no difference. The reviews list also now loads each author's profile in the same query.

---

## 4. Auth throttling and OTP protection

The sign-up, password-reset and delete-account codes are 4 digits, so they are only safe if guesses are scarce. The server now limits guesses **per email address**, which an attacker cannot avoid by changing IP.

### Before

No rate limits anywhere. All 10,000 codes could be tried inside the 10-minute code lifetime, or the email endpoints spammed. Codes came from Python's `random` (not designed for security). Each email is sent from a raw background thread (not changed yet).

### Now

| Limit | Applies to | Rate | Keyed by |
| --- | --- | --- | --- |
| OTP guesses (`otp_verify`) | verify code, complete sign-up, reset confirm, delete account | 10 / hour | Email (case-insensitive) |
| OTP emails (`otp_send`) | register init, resend, password-reset request, delete-account init | 6 / hour | Email |
| Auth endpoints (`auth_ip`) | login, register init, resend, verify, reset | 30 / minute | IP address |
| Username check (`username_check`) | `check-username` | 60 / minute | IP address |
| Partner requests (`partner_request`) | public "join as partner" form | 5 / hour | IP address |

- Codes are generated with `secrets` and are still 4 digits.
- A user who hits a limit sees: *"Too many attempts. Please try again in N minutes."* (`friendly_exception_handler` in `users/throttles.py`). Optional app improvement: disable the resend button after that message.
- Counters live in Redis (`REDIS_URL`), shared by every server process. This needs `DEBUG=False`; `django-redis` is now in `requirements.txt`.

The per-email limits are the real protection. The per-IP limits only slow bulk abuse and depend on `NUM_PROXIES` (section 7).

### The rates in `settings.py`

```python
"DEFAULT_THROTTLE_RATES": {
    "auth_ip": "30/min",
    "username_check": "60/min",
    "partner_request": "5/hour",
    "otp_send": "6/hour",
    "otp_verify": "10/hour",
},
```

This is just the table of limits. Each key is the name (`scope`) of a throttle class in `users/throttles.py`; each value is "how many requests / per what period" before the server answers `429 Too Many Requests`. The names do nothing on their own, a view only uses a limit if it lists that throttle in its `throttle_classes`. To loosen or tighten a limit, change only the number (periods allowed: `sec`, `min`, `hour`, `day`).

---

## 5. Atomic deal claiming

Claiming a deal now locks that deal while the limits are checked and the claim is saved, so two simultaneous claims can no longer both succeed past a limit.

### Before

The endpoint checked "is the deal active and has this user reached the limit?" and only afterwards saved the claim and added 1 to `used_count`. A second request in between (double tap, two devices) passed the same check. A deal with `max_uses = 100` could be claimed 101 times, or a one-per-user deal twice. The 6-digit redemption code was retried in an endless loop on collision.

### Now (`create_deal_use_with_redemption`, `restaurants/services.py`)

1. Start a transaction and lock the deal's row.
2. Re-check with the locked row: deal active, `used_count` below `max_uses`, user below `max_per_user`.
3. Save the claim with a unique redemption code (retries capped at 20) and add 1 to `used_count`.
4. Release the lock, then generate the QR image. If the QR step fails, the claim is undone, as before.

If a request loses the race the app gets the same `400` with `{"error": "..."}` it already gets from the earlier checks, so no app change is needed. Redemption codes now come from `secrets`. Previously the whole function ran inside one transaction including the QR work; now only check-and-save does, so the lock is held briefly.

**Caveat:** the tests cover the limit logic on SQLite, which ignores row locks, so they do not prove behaviour under truly parallel requests. On a Postgres staging database, fire 20 simultaneous claims at a `max_uses = 5` deal and confirm exactly 5 succeed.

---

## 6. Database index

One index was added because the hot queries were already well indexed (an index speeds reads but slightly slows writes, so unneeded ones are a cost).

- **Added:** `mysteryvisit_latest_idx` on `MysteryVisit (restaurant, status, -submitted_at)`. It serves "latest submitted mystery visit per restaurant", used by the leaderboard score.
- **Already present:** `Review (restaurant, rating)`, `Deal (restaurant, is_active)`, `DealUse (user, deal)`, plus foreign-key indexes.
- **Migration:** `restaurants/migrations/0023_mysteryvisit_latest_index.py`. Only creates the index; no data changes. On a large Postgres table run it at a quiet time, as index creation briefly blocks writes.

---

## 7. NUM_PROXIES: what it is and how to set it

`NUM_PROXIES` tells Django how many servers sit between the internet and the app, so the per-IP rate limits count the real user and not the server in front. You set it yourself with one line in the server's `.env`; no code or app change.

### Why it exists

A request usually passes through a front server first (nginx, sometimes also Cloudflare or a load balancer). Django then sees the front server's address as the sender. Each front server adds the address it received the request from to the end of a list in the `X-Forwarded-For` header. The rate limiter reads that header to find the real IP.

A user can also send their own fake `X-Forwarded-For`. If Django doesn't know how many trusted servers are in front, it can't tell which entry is real, so an attacker could change the fake entry on every request and look like a new person each time. `NUM_PROXIES = N` tells Django to count from the **end** of the list, taking the Nth address from the right, which your own servers wrote.

### Which number does what

| Value | What Django does | Use when |
| --- | --- | --- |
| unset (default) | Uses the whole `X-Forwarded-For` header text as the user's identity, or the direct address if no header. Behaves as before this change. | Not sure, or no proxy |
| `0` | Ignores the header, uses the direct connection address only | Gunicorn exposed directly. (Not supported by this setup's env switch, which sets only digits; `0` works too, but unset is the same in practice.) |
| `1` | Takes the **last** address in the header | One server in front: nginx only |
| `2` | Takes the **second from last** address | Two in front: Cloudflare/load balancer → nginx |
| `3` | Takes the third from last | Three layers (e.g. Cloudflare → load balancer → nginx) |

Rule: count the servers that forward requests to Django, and use that number.

To check, on the server run `grep -r "X-Forwarded-For" /etc/nginx/` and `grep -r proxy_pass /etc/nginx/`. A line like `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` plus `proxy_pass http://127.0.0.1:8000;` means nginx is one proxy. Then check whether your DNS points at Cloudflare or a load balancer first.

### Production value for this project: `NUM_PROXIES=1`

Checked on the AWS server (read-only inspection, 2026-10-10):

- Request path: internet → nginx (ports 80/443) → gunicorn on `127.0.0.1:8000` (2 workers).
- `/etc/nginx/sites-available/discountbuddy` contains `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`, so nginx adds exactly one entry to the header.
- `discountbuddy.markitupgroup.com` resolves directly to the server's IP (`13.51.168.80`) and answers as `nginx/1.24.0`, with no Cloudflare or load-balancer headers.

One proxy in front of Django, so the value is **1**. If Cloudflare or a load balancer is ever put in front of nginx, change it to 2 (and re-check with the commands above).

### How to set it

1. Open the project's `.env` on the server.
2. Add `NUM_PROXIES=1` (your number).
3. Restart the app process.

`discount_buddy/settings.py` reads it and applies it only if it is a whole number.

### Risk of a wrong value

- **Too small** is the dangerous mistake. Real count 2, set 1: Django sees only the Cloudflare/load-balancer address for every user, so all users share one bucket of 30 login attempts a minute and people get blocked.
- **Too large** is less harmful but weakens protection: Django picks an address earlier in the list, which an attacker can fake.

That's why the default is unset. After setting it, check that two phones on different networks can both log in repeatedly without blocking each other.

---

## 8. Server configuration findings (AWS, 2026-10-10)

Found by reading the live server's configuration. Nothing was changed.

| Setting (server `.env`) | Current value | Effect | Recommended |
| --- | --- | --- | --- |
| `DJANGO_DEBUG` | `True` | `settings.py` uses the **Redis cache only when DEBUG is off**. With it on, the cache is per process (`LocMemCache`), so each of the 2 gunicorn workers counts rate limits separately, making them about half as strict, and they are not shared via the Redis on `127.0.0.1:6379` even though `REDIS_URL` is set. DEBUG on in production also exposes detailed error pages. | `False`, after checking the other settings below |
| `CELERY_TASK_ALWAYS_EAGER` | not set (defaults to `"True"`) | Push notifications run inside the web request even though a Celery worker is running (idle). A slow FCM call blocks a gunicorn worker. | `False`, as long as the Celery worker stays up |
| `NUM_PROXIES` | not set | Per-IP throttle can be sidestepped with a fake `X-Forwarded-For`. | `1` (section 7) |
| `REDIS_URL` | set (`redis://localhost:6379/1`) | Used for the cache only when DEBUG is off. Celery uses it as the broker either way. | keep |

Before setting `DJANGO_DEBUG=False`, also check: `DJANGO_SECRET_KEY` is set in `.env` (the code falls back to `"change-me-in-production"`, and changing the key logs every user out), static files are served by nginx (`/static/` → `staticfiles/`, already configured), and `collectstatic` has been run.

Other server facts: Postgres listens on `127.0.0.1:5432`, Redis on `127.0.0.1:6379` (both local only), and the Celery worker runs from `~/Discount-Buddy/venv`.

---

## 9. Deploy checklist, rollback, caveats

The changes are written and tested but not committed or deployed.

- [ ] Server `DJANGO_DEBUG` is `True` today, so throttle counters are per worker until it is `False` (section 8); decide when to switch
- [ ] Pull the code; `pip install -r requirements.txt` (adds `django-redis`)
- [ ] `python manage.py migrate` (applies the one index; quiet time on a large table)
- [ ] Add `NUM_PROXIES=1` to the server `.env`
- [ ] Restart the app process
- [ ] Smoke test: log in, open home, claim a deal, post and edit a review
- [ ] On Postgres staging, fire 20 simultaneous claims at a `max_uses = 5` deal; exactly 5 should succeed

**Rollback:** revert the code and restart. The index is harmless if left; no data was changed.

### Known caveats

- `db.sqlite3` is tracked in git and was modified by test runs. Do not commit it.
- `/restaurants?ordering=rating` returns a server error because `rating` is not a real field. Existed before; not changed.
- OTP emails are still sent from a raw background thread per request. Moving them to a queue is a good next step.
- Still open from the audit: `ALLOWED_HOSTS` is `*`, the secret key and `DEBUG` have unsafe defaults, and Celery tasks run inline unless `CELERY_TASK_ALWAYS_EAGER` is false. These depend on how the server is configured and were deliberately not touched.
