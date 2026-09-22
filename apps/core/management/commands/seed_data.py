"""Populate the database with a believable demo catalogue.

    python manage.py seed_data            # add/update demo content
    python manage.py seed_data --fresh    # wipe demo content first
    python manage.py seed_data --no-demo-bookings

Everything is created with ``update_or_create`` keyed on the slug, so running
the command twice is safe and will not duplicate rows.

About the images
----------------
Seed rows use the ``image_url`` fallback field rather than uploaded files, so
the repository ships no binaries and the command needs no network access at
run time. Photos come from picsum.photos with a fixed seed, which means the
same trip always shows the same picture. Real photography is meant to be
drag-and-dropped over the top in the admin — the uploaded file always wins.
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.bookings.models import Booking, Coupon
from apps.core.models import NewsletterSubscriber, Testimonial
from apps.destinations.models import (
    Category,
    Destination,
    DestinationImage,
    ItineraryDay,
    Package,
    PackageImage,
)
from apps.reviews.models import Review

User = get_user_model()

# Deterministic randomness so the demo data looks the same on every machine.
RNG = random.Random(20250921)


def photo(seed: str, width: int = 1600, height: int = 1000) -> str:
    """A stable placeholder photo URL for a given seed string."""
    return f"https://picsum.photos/seed/{seed}/{width}/{height}"


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
CATEGORIES = [
    ("Beaches", "🏝️", "Sand, salt and very little signal.", True),
    ("Mountains", "🏔️", "Thin air, thick memories.", True),
    ("Heritage", "🏛️", "Old stones with good stories.", True),
    ("Road trips", "🚐", "The detour is the point.", True),
    ("Wildlife", "🐘", "Sunrise safaris and patient waiting.", False),
    ("Nightlife", "🎧", "Cities that start after dark.", False),
    ("Wellness", "🧘", "Slow mornings, no itinerary guilt.", True),
    ("Adventure", "🪂", "For people who read this list first.", True),
]


# ---------------------------------------------------------------------------
# Destinations and their trips
# ---------------------------------------------------------------------------
DESTINATIONS = [
    {
        "name": "Bali",
        "country": "Indonesia",
        "region": "Lesser Sunda Islands",
        "tagline": "Rice terraces, reef breaks and the best coffee you'll have all year.",
        "description": (
            "Bali packs a startling amount into one island. Mornings belong to Ubud's "
            "terraced valleys and the temples tucked behind them; afternoons belong to "
            "the surf towns along the south coast. The island is small enough that you "
            "can eat breakfast in the jungle and watch the sunset from a cliff bar, and "
            "busy enough that you'll want a plan for the bits in between."
        ),
        "best_time": "April to October",
        "lat": -8.4095,
        "lng": 115.1889,
        "featured": True,
        "categories": ["Beaches", "Wellness"],
        "packages": [
            {
                "title": "Bali Unfiltered: Ubud, Canggu & the Nusa Islands",
                "summary": "Nine days across jungle, surf town and island, at a pace that still lets you sleep in.",
                "price": "68900",
                "discount": "58900",
                "days": 9,
                "nights": 8,
                "difficulty": "easy",
                "max_guests": 14,
                "featured": True,
                "categories": ["Beaches", "Wellness"],
                "highlights": [
                    "Sunrise at Tegallalang before the tour buses arrive",
                    "A surf lesson in Canggu with a coach who does not shout",
                    "Two nights on Nusa Penida with a private boat to Kelingking",
                    "A silent-morning session at a working Balinese temple",
                ],
                "inclusions": [
                    "8 nights in boutique stays, twin sharing",
                    "Daily breakfast and 4 dinners",
                    "All airport and inter-island transfers",
                    "Surf lesson with board hire",
                    "English-speaking local host for the whole trip",
                ],
                "exclusions": [
                    "International flights",
                    "Indonesian visa on arrival",
                    "Travel insurance",
                    "Anything at the bar after dinner",
                ],
                "itinerary": [
                    ("Land in Denpasar, drift to Ubud", "Your host meets you at arrivals and drives you north. Nothing is scheduled tonight beyond dinner on a terrace above the river valley.", "Dinner", "Komaneka-style jungle suite, Ubud"),
                    ("Terraces at first light", "Out by 5:30am for Tegallalang while the mist still sits in the valley. Back for a long breakfast, then a free afternoon for the Ubud market or a nap — both defensible.", "Breakfast", "Ubud"),
                    ("Temples and the Campuhan ridge", "A morning at Tirta Empul, an afternoon walk along the ridge, and a cooking session with a family in Penestanan.", "Breakfast, dinner", "Ubud"),
                    ("South to Canggu", "A two-hour drive to the coast. Check in, then your first surf lesson on the beach break at Batu Bolong.", "Breakfast", "Canggu"),
                    ("Surf, eat, repeat", "Second surf session at dawn. The rest of the day is deliberately empty — Canggu rewards wandering.", "Breakfast", "Canggu"),
                    ("Boat to Nusa Penida", "Fast boat from Sanur. The island is rougher than the mainland and far emptier.", "Breakfast, dinner", "Nusa Penida"),
                    ("Kelingking and the west coast", "Private boat around the cliffs, snorkelling with manta rays at Manta Point if the swell allows.", "Breakfast, lunch", "Nusa Penida"),
                    ("Back to the mainland", "Return boat and a slow final evening in Seminyak, with dinner somewhere loud and good.", "Breakfast, dinner", "Seminyak"),
                    ("Fly home", "Late checkout and an airport transfer whenever your flight goes.", "Breakfast", "—"),
                ],
            },
            {
                "title": "Ubud Reset: Five Slow Days",
                "summary": "Yoga, waterfalls and long lunches. No alarm clocks unless you set one.",
                "price": "34500",
                "discount": None,
                "days": 5,
                "nights": 4,
                "difficulty": "easy",
                "max_guests": 10,
                "featured": False,
                "categories": ["Wellness"],
                "highlights": [
                    "Daily morning yoga overlooking the Ayung valley",
                    "A Balinese healer session, if you want one",
                    "Two waterfall mornings with no crowds",
                ],
                "inclusions": [
                    "4 nights in a valley-view room",
                    "Daily breakfast and yoga",
                    "Airport transfers",
                    "One spa treatment",
                ],
                "exclusions": ["Flights", "Visa", "Lunches and dinners"],
                "itinerary": [
                    ("Arrive and exhale", "Transfer from the airport, an orientation walk, and dinner in the garden.", "Dinner", "Ubud"),
                    ("Yoga and the Ayung valley", "Morning practice, then a guided walk down into the valley and back up for lunch.", "Breakfast", "Ubud"),
                    ("Waterfalls", "An early start to Tibumana and Tegenungan before the day-trippers.", "Breakfast", "Ubud"),
                    ("Spa and nothing else", "Deliberately unscheduled. Your treatment is booked for whenever you like.", "Breakfast", "Ubud"),
                    ("Home", "Breakfast, checkout, transfer.", "Breakfast", "—"),
                ],
            },
        ],
    },
    {
        "name": "Ladakh",
        "country": "India",
        "region": "Ladakh",
        "tagline": "Cold desert, impossible passes and a sky that looks fake in photos.",
        "description": (
            "Ladakh sits above 3,000 metres and behaves accordingly — the light is "
            "harder, the air is thinner and distances take longer than the map suggests. "
            "That is the appeal. Monasteries cling to ridgelines, the Indus runs green "
            "through brown valleys, and the road to Pangong is still one of the great "
            "drives anywhere."
        ),
        "best_time": "June to September",
        "lat": 34.1526,
        "lng": 77.5771,
        "featured": True,
        "categories": ["Mountains", "Road trips", "Adventure"],
        "packages": [
            {
                "title": "Ladakh Overland: Leh to Pangong to Nubra",
                "summary": "Seven days, three valleys and two of the highest motorable passes on earth.",
                "price": "52000",
                "discount": "46800",
                "days": 7,
                "nights": 6,
                "difficulty": "moderate",
                "max_guests": 12,
                "featured": True,
                "categories": ["Mountains", "Road trips"],
                "highlights": [
                    "Two nights camped beside Pangong Tso",
                    "Khardung La and Chang La on the same trip",
                    "Sunrise at Thiksey monastery during morning prayers",
                    "Double-humped camels on the Hunder dunes",
                ],
                "inclusions": [
                    "6 nights (hotels in Leh, deluxe camps elsewhere)",
                    "All meals from dinner on day 1",
                    "Private vehicle with an oxygen cylinder on board",
                    "Inner Line Permits",
                    "Mountain-trained driver-guide",
                ],
                "exclusions": ["Flights to Leh", "Monastery camera fees", "Personal gear"],
                "itinerary": [
                    ("Land in Leh, do nothing", "Acclimatisation is the whole job today. You will be told to rest, and you should listen.", "Dinner", "Leh"),
                    ("Monasteries and the Indus valley", "Thiksey at dawn for prayers, then Hemis and Shey at an unhurried pace.", "All meals", "Leh"),
                    ("Over Chang La to Pangong", "Five hours of climbing, a pass at 5,360m, then the lake appears and stops the conversation.", "All meals", "Pangong camp"),
                    ("Pangong, slowly", "Sunrise over the water, a walk along the shore to Merak, and a very early night.", "All meals", "Pangong camp"),
                    ("Nubra via Shyok", "The rough, beautiful river road north to Hunder and the dunes.", "All meals", "Hunder"),
                    ("Diskit and Khardung La", "The big Maitreya Buddha in the morning, then back to Leh over the top.", "All meals", "Leh"),
                    ("Fly out", "Early transfer for the morning flight — the only one that reliably gets out.", "Breakfast", "—"),
                ],
            },
        ],
    },
    {
        "name": "Kyoto",
        "country": "Japan",
        "region": "Kansai",
        "tagline": "A thousand temples and the most disciplined breakfast of your life.",
        "description": (
            "Kyoto rewards early risers and slow walkers. Arashiyama's bamboo is a "
            "different place at 6am than at 10am, and the eastern hills hide stone lanes "
            "that most visitors never find. Come for the temples, stay for the food — "
            "this is a city where a lunch counter with six seats can change your standards."
        ),
        "best_time": "March to May, October to November",
        "lat": 35.0116,
        "lng": 135.7681,
        "featured": True,
        "categories": ["Heritage", "Wellness"],
        "packages": [
            {
                "title": "Kyoto in Autumn: Temples, Trails & Kaiseki",
                "summary": "Six days chasing maple season through the eastern hills, with a serious food itinerary.",
                "price": "129000",
                "discount": "114900",
                "days": 6,
                "nights": 5,
                "difficulty": "easy",
                "max_guests": 8,
                "featured": True,
                "categories": ["Heritage"],
                "highlights": [
                    "Arashiyama bamboo grove before sunrise, genuinely empty",
                    "A full kaiseki dinner with a chef who explains every course",
                    "The Philosopher's Path at peak colour",
                    "A tea ceremony in a private machiya townhouse",
                ],
                "inclusions": [
                    "5 nights in a restored machiya, twin sharing",
                    "Daily breakfast, 2 kaiseki dinners",
                    "JR transfers from Kansai airport",
                    "Private guide for 3 of the 6 days",
                    "All temple entries",
                ],
                "exclusions": ["International flights", "Lunches", "Shinkansen day trips"],
                "itinerary": [
                    ("Arrive in Kyoto", "Airport express from Kansai, check into the machiya, then a walk through Gion at dusk.", "Dinner", "Machiya, Nakagyo"),
                    ("Arashiyama at dawn", "Out at 5:45am for the bamboo grove and Tenryu-ji before anyone else. Afternoon free.", "Breakfast", "Nakagyo"),
                    ("The eastern hills", "Kiyomizu-dera, the stone lanes of Ninen-zaka, and Kodai-ji lit up after dark.", "Breakfast, dinner", "Nakagyo"),
                    ("Fushimi Inari and tea", "The full gate circuit up the mountain, then a private tea ceremony in the afternoon.", "Breakfast", "Nakagyo"),
                    ("Philosopher's Path", "A slow north-to-south walk via Ginkaku-ji, ending with kaiseki.", "Breakfast, dinner", "Nakagyo"),
                    ("Depart", "Nishiki market for last-minute food, then the train to Kansai.", "Breakfast", "—"),
                ],
            },
        ],
    },
    {
        "name": "Santorini",
        "country": "Greece",
        "region": "Cyclades",
        "tagline": "A drowned volcano with the best dinner view in the Mediterranean.",
        "description": (
            "Santorini is a caldera rim you can walk end to end, with villages stacked "
            "down the cliff face and black-sand beaches on the far side. Oia gets the "
            "postcards and the crowds; the rest of the island — Pyrgos, Emporio, the "
            "wineries inland — is where the days actually get good."
        ),
        "best_time": "May to June, September to October",
        "lat": 36.3932,
        "lng": 25.4615,
        "featured": True,
        "categories": ["Beaches", "Heritage"],
        "packages": [
            {
                "title": "Santorini & Naxos: Two Islands, One Ferry",
                "summary": "Eight days pairing the famous caldera with the island Greeks actually holiday on.",
                "price": "148000",
                "discount": None,
                "days": 8,
                "nights": 7,
                "difficulty": "easy",
                "max_guests": 10,
                "featured": True,
                "categories": ["Beaches"],
                "highlights": [
                    "The Fira-to-Oia caldera walk, done early and downhill",
                    "A catamaran day with swimming stops at the hot springs",
                    "Assyrtiko tasting at a family winery inland",
                    "Three nights on Naxos, where dinner costs a third as much",
                ],
                "inclusions": [
                    "7 nights (4 Santorini, 3 Naxos)",
                    "Daily breakfast",
                    "Inter-island ferry tickets",
                    "Catamaran day with lunch",
                    "Winery tour and tasting",
                ],
                "exclusions": ["Flights", "Most dinners", "Scooter or car hire on Naxos"],
                "itinerary": [
                    ("Arrive Santorini", "Transfer to Imerovigli, then the first of many caldera sunsets.", "Dinner", "Imerovigli"),
                    ("The caldera walk", "Fira to Oia on foot, starting at 7am. Afternoon by the pool, because you earned it.", "Breakfast", "Imerovigli"),
                    ("Catamaran day", "Red Beach, White Beach, the hot springs and lunch on board.", "Breakfast, lunch", "Imerovigli"),
                    ("Inland Santorini", "Pyrgos, Emporio and a long afternoon at a winery that predates the tourism.", "Breakfast", "Imerovigli"),
                    ("Ferry to Naxos", "Two hours across. Naxos Town's Venetian quarter in the evening.", "Breakfast", "Naxos Town"),
                    ("Mountain villages", "Halki, Apeiranthos and the marble quarries, with lunch at a taverna with four tables.", "Breakfast, lunch", "Naxos Town"),
                    ("Beach day", "Plaka and Mikri Vigla, both long and mostly empty.", "Breakfast", "Naxos Town"),
                    ("Depart", "Morning ferry or flight out of Naxos.", "Breakfast", "—"),
                ],
            },
        ],
    },
    {
        "name": "Reykjavík",
        "country": "Iceland",
        "region": "Capital Region",
        "tagline": "Waterfalls, black sand and a decent chance of the aurora.",
        "description": (
            "Iceland in winter is short on daylight and long on drama. The south coast "
            "delivers a waterfall every forty minutes, the glacier lagoon is genuinely "
            "surreal, and when the sky clears the aurora does the rest. Reykjavík itself "
            "is small, walkable and far warmer than the weather suggests."
        ),
        "best_time": "September to March for aurora, June to August for midnight sun",
        "lat": 64.1466,
        "lng": -21.9426,
        "featured": True,
        "categories": ["Adventure", "Road trips"],
        "packages": [
            {
                "title": "Iceland's South Coast & Northern Lights",
                "summary": "Six winter days from Reykjavík to Jökulsárlón, with three aurora nights built in.",
                "price": "172000",
                "discount": "159000",
                "days": 6,
                "nights": 5,
                "difficulty": "moderate",
                "max_guests": 12,
                "featured": True,
                "categories": ["Adventure"],
                "highlights": [
                    "Walking behind Seljalandsfoss in full winter kit",
                    "Icebergs at Jökulsárlón and the Diamond Beach at sunrise",
                    "A glacier hike on Sólheimajökull with crampons",
                    "Three aurora nights outside the city's light dome",
                ],
                "inclusions": [
                    "5 nights including 2 in a remote aurora-view lodge",
                    "Daily breakfast and 3 dinners",
                    "4x4 transport with a glacier-certified guide",
                    "Glacier hike with all technical gear",
                    "Blue Lagoon entry on the final day",
                ],
                "exclusions": ["Flights", "Lunches", "Alcohol"],
                "itinerary": [
                    ("Land at Keflavík", "Transfer to Reykjavík, an orientation walk and an early night.", "Dinner", "Reykjavík"),
                    ("Golden Circle", "Þingvellir, Geysir and Gullfoss, ending at a lodge in the south with dark skies.", "Breakfast, dinner", "South coast lodge"),
                    ("Waterfall day", "Seljalandsfoss, Skógafoss and the black sands at Reynisfjara.", "Breakfast", "Vík"),
                    ("Glacier and lagoon", "Morning hike on Sólheimajökull, afternoon at Jökulsárlón and the Diamond Beach.", "Breakfast, dinner", "Höfn"),
                    ("Back west", "A long, spectacular drive returning to Reykjavík with stops as the light allows.", "Breakfast", "Reykjavík"),
                    ("Blue Lagoon and out", "A soak on the way to the airport, which is the correct order.", "Breakfast", "—"),
                ],
            },
        ],
    },
    {
        "name": "Rishikesh",
        "country": "India",
        "region": "Uttarakhand",
        "tagline": "White water, cliff jumps and the Ganga at 6am.",
        "description": (
            "Rishikesh is two towns in one: the ashram side, all bells and river aartis, "
            "and the adventure side upstream, where rafting companies run Grade III and "
            "IV rapids from March through June. Do both. The Himalaya starts just behind "
            "the ridge and it shows."
        ),
        "best_time": "September to June",
        "lat": 30.0869,
        "lng": 78.2676,
        "featured": False,
        "categories": ["Adventure", "Wellness"],
        "packages": [
            {
                "title": "Rishikesh Weekend: Rapids & Riverside Camp",
                "summary": "Three days of rafting, cliff jumping and bonfires on the sand.",
                "price": "8900",
                "discount": "7400",
                "days": 3,
                "nights": 2,
                "difficulty": "moderate",
                "max_guests": 20,
                "min_guests": 2,
                "featured": True,
                "categories": ["Adventure"],
                "highlights": [
                    "16km of Grade III rapids from Shivpuri",
                    "Cliff jumping at the Body Surfing stretch",
                    "Riverside tents on a private beach",
                    "The Parmarth Niketan evening aarti",
                ],
                "inclusions": [
                    "2 nights in riverside Swiss tents",
                    "All meals from lunch day 1",
                    "Rafting with certified guides and all gear",
                    "Bonfire and music each night",
                ],
                "exclusions": ["Transport to Rishikesh", "Bungee jumping", "Personal expenses"],
                "itinerary": [
                    ("Arrive and raft", "Check into camp by noon, then the afternoon run from Shivpuri to Rishikesh.", "Lunch, dinner", "Riverside camp"),
                    ("Full-day river", "The long 26km stretch with a beach lunch, followed by an evening at the aarti.", "All meals", "Riverside camp"),
                    ("Trek and out", "A short waterfall trek before checkout at 11am.", "Breakfast", "—"),
                ],
            },
        ],
    },
    {
        "name": "Queenstown",
        "country": "New Zealand",
        "region": "Otago",
        "tagline": "The adventure capital, and it is not marketing.",
        "description": (
            "Queenstown sits on a lake ringed by the Remarkables, and every activity you "
            "have heard of was probably invented here. Bungee, jetboats, skydives and "
            "helicopter landings on glaciers all operate within an hour of town. So does "
            "some of the best hiking in the southern hemisphere, which costs nothing."
        ),
        "best_time": "December to March, June to August for ski",
        "lat": -45.0312,
        "lng": 168.6626,
        "featured": False,
        "categories": ["Adventure", "Mountains"],
        "packages": [
            {
                "title": "Queenstown & Milford Sound",
                "summary": "Seven days of alpine hiking, one very big fjord and as much adrenaline as you order.",
                "price": "195000",
                "discount": None,
                "days": 7,
                "nights": 6,
                "difficulty": "challenging",
                "max_guests": 10,
                "featured": False,
                "categories": ["Adventure", "Mountains"],
                "highlights": [
                    "The Routeburn Track day section",
                    "A cruise to the Tasman Sea through Milford Sound",
                    "Ben Lomond summit, if the group is up for it",
                    "One included adrenaline activity of your choice",
                ],
                "inclusions": [
                    "6 nights in Queenstown and Te Anau",
                    "Daily breakfast and 3 dinners",
                    "Milford Sound cruise and coach",
                    "Guided hiking days with a DOC-licensed guide",
                    "One activity voucher (bungee, jet boat or skydive)",
                ],
                "exclusions": ["Flights", "Extra activities", "Ski passes"],
                "itinerary": [
                    ("Arrive Queenstown", "Transfer from the airport and a gondola ride for the view before dinner.", "Dinner", "Queenstown"),
                    ("Lake day", "Glenorchy road, a short hike at the head of the lake, and a free afternoon.", "Breakfast", "Queenstown"),
                    ("The Routeburn", "A guided day section of the Great Walk. Long, steep and worth it.", "Breakfast, dinner", "Queenstown"),
                    ("To Te Anau", "Drive south, stopping at Mirror Lakes. Evening walk along the Te Anau waterfront.", "Breakfast", "Te Anau"),
                    ("Milford Sound", "The Homer Tunnel road, then a two-hour cruise out to the open sea.", "Breakfast, dinner", "Te Anau"),
                    ("Back north, your call", "Return to Queenstown. The afternoon is yours — this is when the bungee voucher gets used.", "Breakfast", "Queenstown"),
                    ("Depart", "Airport transfer.", "Breakfast", "—"),
                ],
            },
        ],
    },
    {
        "name": "Lisbon",
        "country": "Portugal",
        "region": "Lisboa",
        "tagline": "Tiled hills, tram 28 and dinner that starts at ten.",
        "description": (
            "Lisbon is built on seven hills and makes you feel every one of them. The "
            "reward is a city of viewpoints, azulejo façades and a food scene that has "
            "quietly become one of Europe's best. Sintra is forty minutes away by train, "
            "and the Atlantic beaches are closer than that."
        ),
        "best_time": "March to June, September to October",
        "lat": 38.7223,
        "lng": -9.1393,
        "featured": True,
        "categories": ["Heritage", "Nightlife"],
        "packages": [
            {
                "title": "Lisbon, Sintra & the Alentejo Coast",
                "summary": "Six days of miradouros, palaces and empty Atlantic beaches an hour south.",
                "price": "96500",
                "discount": "88900",
                "days": 6,
                "nights": 5,
                "difficulty": "easy",
                "max_guests": 12,
                "featured": True,
                "categories": ["Heritage", "Beaches"],
                "highlights": [
                    "A tasca crawl through Alfama with a fado stop",
                    "Pena Palace and the Quinta da Regaleira wells at Sintra",
                    "Two days on the Alentejo coast, which is nearly empty",
                    "Pastéis de Belém, eaten standing up like a local",
                ],
                "inclusions": [
                    "5 nights (3 Lisbon, 2 Comporta)",
                    "Daily breakfast and 2 dinners",
                    "Sintra day with a private driver",
                    "Food walk in Alfama",
                    "Train and transfer tickets",
                ],
                "exclusions": ["Flights", "Most meals", "Surf lessons in Comporta"],
                "itinerary": [
                    ("Arrive in Lisbon", "Settle into Príncipe Real, then a sunset miradouro and dinner nearby.", "Dinner", "Príncipe Real"),
                    ("Alfama and Belém", "Tram 28 up, walk down through Alfama, then Belém in the afternoon.", "Breakfast", "Príncipe Real"),
                    ("Sintra", "Pena, Regaleira and Cabo da Roca with a driver, avoiding the queues.", "Breakfast, dinner", "Príncipe Real"),
                    ("South to Comporta", "An hour's drive to rice paddies and pine forest behind 12km of beach.", "Breakfast", "Comporta"),
                    ("Beach and nothing", "Deliberately empty. Surf, horse ride or read — all available, none compulsory.", "Breakfast", "Comporta"),
                    ("Back and out", "Return to Lisbon for the flight.", "Breakfast", "—"),
                ],
            },
        ],
    },
    {
        "name": "Cape Town",
        "country": "South Africa",
        "region": "Western Cape",
        "tagline": "A mountain in the middle of a city, with wine country behind it.",
        "description": (
            "Cape Town has geography most cities would kill for: Table Mountain in the "
            "centre, two oceans on either side of the peninsula, and the Cape Winelands "
            "an hour inland. Add a serious restaurant scene and it is hard to argue with "
            "the hype."
        ),
        "best_time": "November to March",
        "lat": -33.9249,
        "lng": 18.4241,
        "featured": False,
        "categories": ["Wildlife", "Adventure", "Road trips"],
        "packages": [
            {
                "title": "Cape Peninsula & Safari Combo",
                "summary": "Ten days pairing Table Mountain and the Winelands with three nights in a private game reserve.",
                "price": "215000",
                "discount": "198000",
                "days": 10,
                "nights": 9,
                "difficulty": "moderate",
                "max_guests": 8,
                "featured": True,
                "categories": ["Wildlife", "Adventure"],
                "highlights": [
                    "Sunrise hike up Platteklip Gorge, down by cable car",
                    "Six game drives in a malaria-free private reserve",
                    "Cape Point, Boulders Beach penguins and Chapman's Peak in one day",
                    "Two days tasting through Stellenbosch and Franschhoek",
                ],
                "inclusions": [
                    "9 nights including 3 full-board at a game lodge",
                    "Daily breakfast, all meals on safari",
                    "All game drives with a professional ranger",
                    "Private vehicle for the peninsula and Winelands days",
                    "Internal flight to the reserve",
                ],
                "exclusions": ["International flights", "Most city dinners", "Wine purchases"],
                "itinerary": [
                    ("Arrive Cape Town", "Transfer to the City Bowl and an easy first evening.", "Dinner", "City Bowl"),
                    ("Table Mountain", "Up Platteklip at 6am, down by cable car, afternoon at the V&A.", "Breakfast", "City Bowl"),
                    ("The peninsula", "Chapman's Peak, Cape Point, Boulders Beach and back along False Bay.", "Breakfast", "City Bowl"),
                    ("Winelands", "Stellenbosch in the morning, Franschhoek after lunch, with a driver throughout.", "Breakfast, dinner", "Franschhoek"),
                    ("Slow morning, fly east", "A second tasting, then the afternoon flight to the reserve.", "Breakfast, dinner", "Game lodge"),
                    ("Safari", "Dawn and dusk game drives with a long lunch and a nap between them.", "All meals", "Game lodge"),
                    ("Safari", "As yesterday, with a walking safari option in the morning.", "All meals", "Game lodge"),
                    ("Final drive, fly back", "Last dawn drive, then the flight to Cape Town.", "Breakfast", "Camps Bay"),
                    ("Beach and Bo-Kaap", "Camps Bay in the morning, the Bo-Kaap and a food tour in the afternoon.", "Breakfast, dinner", "Camps Bay"),
                    ("Depart", "Airport transfer.", "Breakfast", "—"),
                ],
            },
        ],
    },
    {
        "name": "Goa",
        "country": "India",
        "region": "Goa",
        "tagline": "North for the music, south for the silence. Choose carefully.",
        "description": (
            "Goa is two coastlines wearing one name. The north runs on beach clubs, flea "
            "markets and people who came for a week in 2019. The south is palm groves, "
            "empty sand and shacks that close when the owner feels like it. The "
            "hinterland — spice farms, Portuguese villages, waterfalls — is the part "
            "almost nobody sees."
        ),
        "best_time": "November to February",
        "lat": 15.2993,
        "lng": 74.1240,
        "featured": True,
        "categories": ["Beaches", "Nightlife"],
        "packages": [
            {
                "title": "South Goa Slow: Palolem, Patnem & the Backroads",
                "summary": "Five days on the quiet coast, with a scooter and no fixed plans.",
                "price": "18500",
                "discount": "15900",
                "days": 5,
                "nights": 4,
                "difficulty": "easy",
                "max_guests": 16,
                "featured": True,
                "categories": ["Beaches"],
                "highlights": [
                    "Beach huts twenty steps from the water at Patnem",
                    "A kayak out to Butterfly Beach at sunrise",
                    "Spice plantation lunch in the Western Ghats foothills",
                    "Scooter hire included, because that is how Goa works",
                ],
                "inclusions": [
                    "4 nights in sea-facing huts",
                    "Daily breakfast",
                    "Scooter hire for the whole stay",
                    "Airport transfers",
                    "Spice farm tour with lunch",
                ],
                "exclusions": ["Flights", "Fuel", "Dinners"],
                "itinerary": [
                    ("Arrive, find the sea", "Transfer from Dabolim or Mopa, check in and do nothing.", "—", "Patnem"),
                    ("Palolem and Butterfly", "Sunrise kayak to Butterfly Beach, back for breakfast, afternoon at Palolem.", "Breakfast", "Patnem"),
                    ("Inland day", "Scooter to a spice plantation, then the Netravali bubble lake on the way back.", "Breakfast, lunch", "Patnem"),
                    ("Cabo de Rama", "The fort ruins and the cliff beach below, which is usually empty.", "Breakfast", "Patnem"),
                    ("Depart", "A last swim and an airport transfer.", "Breakfast", "—"),
                ],
            },
        ],
    },
    {
        "name": "Dubai",
        "country": "United Arab Emirates",
        "region": "Dubai",
        "tagline": "Desert, skyline and a brunch culture that takes itself seriously.",
        "description": (
            "Dubai works best when you treat it as two trips. There is the built city — "
            "the tallest building on earth, a metro that runs on time, and shopping as a "
            "civic activity. Then there is the desert an hour out, where the dunes go "
            "orange at sunset and the noise stops entirely."
        ),
        "best_time": "November to March",
        "lat": 25.2048,
        "lng": 55.2708,
        "featured": False,
        "categories": ["Nightlife", "Adventure"],
        "packages": [
            {
                "title": "Dubai in Four: Skyline, Souks & Desert Camp",
                "summary": "A long weekend split between the top of the Burj and a night in the dunes.",
                "price": "42000",
                "discount": None,
                "days": 4,
                "nights": 3,
                "difficulty": "easy",
                "max_guests": 18,
                "featured": False,
                "categories": ["Nightlife"],
                "highlights": [
                    "Burj Khalifa level 148 at golden hour",
                    "An overnight desert camp with dune bashing and a fire",
                    "Old Dubai: the gold souk, the spice souk and an abra across the creek",
                    "A morning at Kite Beach with the skyline behind you",
                ],
                "inclusions": [
                    "2 nights in Downtown, 1 night desert camp",
                    "Daily breakfast and the camp dinner",
                    "Burj Khalifa 148 tickets",
                    "Desert safari with a 4x4 and dune driver",
                ],
                "exclusions": ["Flights", "Visa", "Most meals", "Water park tickets"],
                "itinerary": [
                    ("Arrive and go up", "Check in Downtown, then Burj Khalifa 148 timed for sunset.", "—", "Downtown"),
                    ("Old Dubai", "Abra across the creek, both souks, and the Al Fahidi quarter.", "Breakfast", "Downtown"),
                    ("Into the desert", "Afternoon pickup, dune bashing, camel ride and a camp dinner under the stars.", "Breakfast, dinner", "Desert camp"),
                    ("Beach, then home", "Sunrise over the dunes, back to the city for Kite Beach and the airport.", "Breakfast", "—"),
                ],
            },
        ],
    },
    {
        "name": "Andaman Islands",
        "country": "India",
        "region": "Andaman & Nicobar",
        "tagline": "The clearest water in India, ten hours from anywhere.",
        "description": (
            "The Andamans sit closer to Myanmar than to mainland India, and the water "
            "shows it — visibility on Havelock regularly passes 25 metres. Beyond the "
            "diving there is Neil Island's slow pace, the mangrove creeks, and Ross "
            "Island's colonial ruins being eaten by banyan roots."
        ),
        "best_time": "October to May",
        "lat": 11.7401,
        "lng": 92.6586,
        "featured": False,
        "categories": ["Beaches", "Adventure"],
        "packages": [
            {
                "title": "Havelock & Neil: Reefs, Radhanagar and Ross",
                "summary": "Six days of diving, snorkelling and beaches that make the flight worth it.",
                "price": "44500",
                "discount": "39900",
                "days": 6,
                "nights": 5,
                "difficulty": "easy",
                "max_guests": 14,
                "featured": False,
                "categories": ["Beaches", "Adventure"],
                "highlights": [
                    "Two dives at Nemo Reef and the Wall, gear included",
                    "Sunset at Radhanagar, regularly rated Asia's best beach",
                    "The natural rock bridge at Neil at low tide",
                    "Ross Island's ruins and the light-and-sound show",
                ],
                "inclusions": [
                    "5 nights across Havelock and Neil",
                    "Daily breakfast",
                    "All ferry tickets",
                    "Two guided dives with certified instructors",
                    "Airport and jetty transfers",
                ],
                "exclusions": ["Flights to Port Blair", "Dinners", "Extra dives"],
                "itinerary": [
                    ("Port Blair and Ross", "Land, transfer, and an afternoon at Ross Island and the Cellular Jail show.", "—", "Port Blair"),
                    ("Ferry to Havelock", "Morning catamaran, check in, sunset at Radhanagar.", "Breakfast", "Havelock"),
                    ("Dive day", "Two guided dives in the morning, an empty afternoon at Elephant Beach.", "Breakfast", "Havelock"),
                    ("On to Neil", "Short ferry south. Bharatpur snorkelling and the rock bridge at low tide.", "Breakfast", "Neil"),
                    ("Neil, unhurried", "Laxmanpur for sunset, and very little else on the schedule.", "Breakfast", "Neil"),
                    ("Back to Port Blair", "Ferry and airport transfer.", "Breakfast", "—"),
                ],
            },
        ],
    },
]


TESTIMONIALS = [
    ("Aanya Kulkarni", "@aanyawanders", "Bali Unfiltered", 5,
     "I've booked a lot of trips and this is the first time the itinerary actually "
     "matched the photos. The Ubud sunrise bit is worth every bit of the 5am alarm."),
    ("Rohan Mehta", "@rohanonroute", "Ladakh Overland", 5,
     "They put an oxygen cylinder in the car and told me to sit still on day one. "
     "Two of my friends who booked elsewhere spent day two with altitude sickness. "
     "Small thing, huge difference."),
    ("Tara Fernandes", "@tarafern", "South Goa Slow", 4,
     "Scooter included was the detail that sold me. Four days of turning down random "
     "lanes and finding beaches with nobody on them."),
    ("Ishaan Verma", "@ishaan.v", "Kyoto in Autumn", 5,
     "The bamboo grove at 6am was genuinely empty. By 9am there were four hundred "
     "people there. Timing is the entire product and they know it."),
    ("Meera Nair", "@meeranair", "Iceland's South Coast", 5,
     "Three aurora nights booked in on purpose instead of hoping. We got it on the "
     "second. Guide pulled over at 11pm and just let us stand there."),
    ("Dev Patel", "@devgoeswest", "Cape Peninsula & Safari", 5,
     "Ten days, zero admin. I got a WhatsApp message before every single transfer. "
     "Booking a safari usually means six emails with a lodge — this was one payment."),
]


COUPONS = [
    ("FIRSTTRIP", "15% off your first Travello booking", "percent", "15", "5000", 365, 500),
    ("GENZ500", "Flat ₹500 off — student and under-25 offer", "flat", "500", None, 180, 1000),
    ("MONSOON20", "20% off monsoon-season departures", "percent", "20", "8000", 120, 200),
    ("WELCOME10", "10% off, no minimum spend", "percent", "10", "3000", 365, 2000),
]


REVIEW_SEEDS = [
    (5, "Worth every rupee", "Third trip with Travello and the standard has not slipped once. The local hosts are the difference — ours reshuffled a whole day around bad weather without being asked."),
    (5, "Better than the brochure", "I was braced for the usual gap between what is advertised and what turns up. There wasn't one. Accommodation was a level above what I expected at this price."),
    (4, "Great, with one caveat", "Genuinely excellent trip. Only note is that day four is longer than it reads on paper — bring snacks and don't plan anything for the evening."),
    (5, "The pacing is the point", "Most operators cram in stops so the itinerary looks full. This one leaves gaps on purpose and the trip is far better for it."),
    (4, "Very good value", "Nothing felt cheap and nothing felt padded. The included meals were at proper local places rather than hotel buffets, which I appreciated."),
    (5, "Sorted from start to finish", "Someone met us at every transfer. After a year of self-booking everything, paying for that was an easy decision."),
    (3, "Good trip, busy season", "No complaints about the organisation at all. We just went at peak time and some sites were packed. Go shoulder season if you can."),
    (5, "Our guide made it", "Whatever you are paying the guides, it isn't enough. Knew every back route and got us to the viewpoint before three coaches arrived."),
]


class Command(BaseCommand):
    help = "Load a realistic demo catalogue: destinations, trips, reviews and bookings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing catalogue content before seeding.",
        )
        parser.add_argument(
            "--no-demo-bookings",
            action="store_true",
            help="Skip the sample bookings and reviews.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["fresh"]:
            self.stdout.write(self.style.WARNING("Clearing existing demo content…"))
            Review.objects.all().delete()
            Booking.objects.all().delete()
            Package.objects.all().delete()
            Destination.objects.all().delete()
            Category.objects.all().delete()
            Testimonial.objects.all().delete()
            Coupon.objects.all().delete()

        categories = self._seed_categories()
        self._seed_destinations(categories)
        self._seed_testimonials()
        self._seed_coupons()
        users = self._seed_users()
        self._seed_newsletter()

        if not options["no_demo_bookings"]:
            self._seed_bookings_and_reviews(users)

        self._report()

    # -- pieces -------------------------------------------------------------
    def _seed_categories(self):
        created = {}
        for name, emoji, description, featured in CATEGORIES:
            category, _ = Category.objects.update_or_create(
                name=name,
                defaults={
                    "emoji": emoji,
                    "description": description,
                    "is_featured": featured,
                    "image_url": photo(f"cat-{name.lower().replace(' ', '-')}", 800, 600),
                },
            )
            created[name] = category
        self.stdout.write(f"  categories   {len(created)}")
        return created

    def _seed_destinations(self, categories):
        today = timezone.localdate()
        dest_count = pkg_count = 0

        for entry in DESTINATIONS:
            # Use Django's slugify so the value matches exactly what
            # Destination.save() would generate — anything else produces slugs
            # that cannot be reversed (accented characters, ampersands...).
            slug = slugify(f"{entry['name']}-{entry['country']}")[:120]
            destination, _ = Destination.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": entry["name"],
                    "country": entry["country"],
                    "region": entry["region"],
                    "tagline": entry["tagline"],
                    "description": entry["description"],
                    "best_time_to_visit": entry["best_time"],
                    "latitude": entry["lat"],
                    "longitude": entry["lng"],
                    "is_featured": entry["featured"],
                    "is_active": True,
                    "image_url": photo(f"dest-{slug}"),
                    "meta_description": entry["tagline"][:160],
                },
            )
            dest_count += 1

            # A small gallery so detail pages have something to show.
            destination.gallery.all().delete()
            DestinationImage.objects.bulk_create(
                [
                    DestinationImage(
                        destination=destination,
                        image_url=photo(f"dest-{slug}-{index}"),
                        caption=f"{destination.name} — {caption}",
                        order=index,
                    )
                    for index, caption in enumerate(
                        ["the wide view", "street level", "at golden hour"], start=1
                    )
                ]
            )

            for spec in entry["packages"]:
                package = self._seed_package(destination, spec, categories, today)
                pkg_count += 1

        self.stdout.write(f"  destinations {dest_count}")
        self.stdout.write(f"  trips        {pkg_count}")

    def _seed_package(self, destination, spec, categories, today):
        slug = slugify(spec["title"])[:150]

        package, _ = Package.objects.update_or_create(
            slug=slug,
            defaults={
                "destination": destination,
                "title": spec["title"],
                "summary": spec["summary"],
                "description": (
                    f"{spec['summary']}\n\n{destination.description}\n\n"
                    "Group sizes stay small on purpose, every departure runs with a local "
                    "host, and the itinerary below is the one you actually get — we do not "
                    "quietly swap hotels or drop stops to save money."
                ),
                "price": Decimal(spec["price"]),
                "discount_price": Decimal(spec["discount"]) if spec.get("discount") else None,
                "duration_days": spec["days"],
                "duration_nights": spec["nights"],
                "max_guests": spec.get("max_guests", 12),
                "min_guests": spec.get("min_guests", 1),
                "difficulty": spec["difficulty"],
                "highlights": "\n".join(spec["highlights"]),
                "inclusions": "\n".join(spec["inclusions"]),
                "exclusions": "\n".join(spec["exclusions"]),
                "available_from": today,
                "available_to": today + timedelta(days=365),
                "is_featured": spec.get("featured", False),
                "is_active": True,
                "image_url": photo(f"trip-{slug}"),
                "meta_description": spec["summary"][:160],
            },
        )

        package.categories.set(
            [categories[name] for name in spec["categories"] if name in categories]
        )

        package.gallery.all().delete()
        PackageImage.objects.bulk_create(
            [
                PackageImage(
                    package=package,
                    image_url=photo(f"trip-{slug}-{index}"),
                    caption=f"{package.title} — photo {index}",
                    order=index,
                )
                for index in range(1, 5)
            ]
        )

        package.itinerary.all().delete()
        ItineraryDay.objects.bulk_create(
            [
                ItineraryDay(
                    package=package,
                    day_number=day_number,
                    title=title,
                    description=description,
                    meals=meals,
                    stay=stay,
                )
                for day_number, (title, description, meals, stay) in enumerate(
                    spec["itinerary"], start=1
                )
            ]
        )
        return package

    def _seed_testimonials(self):
        for order, (name, handle, trip, rating, quote) in enumerate(TESTIMONIALS):
            Testimonial.objects.update_or_create(
                name=name,
                defaults={
                    "handle": handle,
                    "trip_taken": trip,
                    "rating": rating,
                    "quote": quote,
                    "order": order,
                    "is_active": True,
                    "avatar_url": photo(f"face-{handle.strip('@')}", 200, 200),
                },
            )
        self.stdout.write(f"  testimonials {len(TESTIMONIALS)}")

    def _seed_coupons(self):
        today = timezone.localdate()
        for code, description, kind, value, cap, days, limit in COUPONS:
            Coupon.objects.update_or_create(
                code=code,
                defaults={
                    "description": description,
                    "discount_type": kind,
                    "value": Decimal(value),
                    "max_discount": Decimal(cap) if cap else None,
                    "valid_from": today - timedelta(days=7),
                    "valid_to": today + timedelta(days=days),
                    "usage_limit": limit,
                    "is_active": True,
                },
            )
        self.stdout.write(f"  coupons      {len(COUPONS)}")

    def _seed_users(self):
        """Create one superuser and a handful of travellers who leave reviews."""
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@travello.test",
                "first_name": "Travello",
                "last_name": "Admin",
                "is_staff": True,
                "is_superuser": True,
                "is_email_verified": True,
            },
        )
        if created:
            admin.set_password("travello123")
            admin.save()

        travellers = []
        people = [
            ("aanya", "Aanya", "Kulkarni", "Mumbai", "India"),
            ("rohan", "Rohan", "Mehta", "Bengaluru", "India"),
            ("tara", "Tara", "Fernandes", "Panaji", "India"),
            ("ishaan", "Ishaan", "Verma", "Delhi", "India"),
            ("meera", "Meera", "Nair", "Kochi", "India"),
            ("dev", "Dev", "Patel", "Ahmedabad", "India"),
            ("demo", "Demo", "Traveller", "Gandhinagar", "India"),
        ]
        for username, first, last, city, country in people:
            user, was_new = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@travello.test",
                    "first_name": first,
                    "last_name": last,
                    "city": city,
                    "country": country,
                    "phone": f"+91 9{RNG.randint(100000000, 999999999)}",
                    "is_email_verified": True,
                },
            )
            if was_new:
                user.set_password("travello123")
                user.save()
            travellers.append(user)

        self.stdout.write(f"  users        {len(travellers) + 1} (admin + {len(travellers)})")
        return travellers

    def _seed_newsletter(self):
        for index in range(1, 25):
            NewsletterSubscriber.objects.get_or_create(
                email=f"subscriber{index}@example.com",
                defaults={"source": RNG.choice(["footer", "home", "checkout"])},
            )

    def _seed_bookings_and_reviews(self, travellers):
        """Back-date a spread of bookings so the analytics dashboard has a shape."""
        if Booking.objects.exists():
            self.stdout.write("  bookings     skipped (already present)")
            return

        packages = list(Package.objects.published())
        if not packages:
            return

        today = timezone.localdate()
        booking_count = review_count = 0
        review_pool = list(REVIEW_SEEDS)

        for months_ago in range(11, -1, -1):
            # More recent months get more bookings — a business that is growing.
            volume = RNG.randint(2, 5) + (11 - months_ago) // 3
            for _ in range(volume):
                package = RNG.choice(packages)
                user = RNG.choice(travellers)
                created = timezone.now() - timedelta(
                    days=months_ago * 30 + RNG.randint(0, 27),
                    hours=RNG.randint(0, 23),
                )
                start = created.date() + timedelta(days=RNG.randint(20, 90))
                adults = RNG.randint(1, min(4, package.max_guests))
                children = RNG.choice([0, 0, 0, 1, 2])
                guests = min(adults + children, package.max_guests)
                pricing = package.quote(guests=guests)

                if start < today:
                    status = RNG.choices(
                        [Booking.STATUS_COMPLETED, Booking.STATUS_CANCELLED],
                        weights=[9, 1],
                    )[0]
                else:
                    status = RNG.choices(
                        [
                            Booking.STATUS_CONFIRMED,
                            Booking.STATUS_PENDING,
                            Booking.STATUS_CANCELLED,
                        ],
                        weights=[7, 2, 1],
                    )[0]

                paid = status in (Booking.STATUS_CONFIRMED, Booking.STATUS_COMPLETED)
                booking = Booking(
                    user=user,
                    package=package,
                    start_date=start,
                    adults=adults,
                    children=children,
                    full_name=user.get_full_name(),
                    email=user.email,
                    phone=user.phone or "+91 9000000000",
                    unit_price=pricing["unit_price"],
                    base_amount=pricing["base_amount"],
                    discount_amount=pricing["discount_amount"],
                    tax_amount=pricing["tax_amount"],
                    total_amount=pricing["total_amount"],
                    status=status,
                    payment_status=(
                        Booking.PAYMENT_PAID if paid else Booking.PAYMENT_UNPAID
                    ),
                )
                booking.save()
                # auto_now_add ignores assignment, so back-date with an update().
                Booking.objects.filter(pk=booking.pk).update(created_at=created)
                booking_count += 1

                # Completed trips sometimes get a review.
                if status == Booking.STATUS_COMPLETED and RNG.random() < 0.55:
                    if Review.objects.filter(package=package, user=user).exists():
                        continue
                    rating, title, comment = RNG.choice(review_pool)
                    Review.objects.create(
                        package=package,
                        user=user,
                        booking=booking,
                        rating=rating,
                        title=title,
                        comment=comment,
                        is_approved=RNG.random() < 0.85,
                    )
                    review_count += 1

        self.stdout.write(f"  bookings     {booking_count}")
        self.stdout.write(f"  reviews      {review_count}")

    def _report(self):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("  Admin login    admin / travello123")
        self.stdout.write("  Traveller      demo / travello123")
        self.stdout.write("  Try the code   FIRSTTRIP at checkout")
