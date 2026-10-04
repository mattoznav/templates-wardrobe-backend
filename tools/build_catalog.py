"""Write the demo catalogue to data/*.csv.

Products, colours, sizes and stock are fictional and defined below. Photos are
real, from Unsplash (https://unsplash.com), used under the Unsplash License
(https://unsplash.com/license): they are not copied into the repository, the
shop loads them from the Unsplash CDN and credits the photographer next to
each image.

Run from the backend folder: `python tools/build_catalog.py`, then
`python manage.py load_data`. Stock levels come from a fixed seed, so the
output is the same on every run.
"""

import csv
import random
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
UNSPLASH_CDN = "https://images.unsplash.com/"

# alias: (Unsplash photo id, CDN path, photographer, Unsplash username)
PHOTOS = {
    "slip-8": ("9kbeSfpdjYs", "photo-1706816997334-c51bcd0f52e0", "Mohamed hamdi", "amdshutter"),
    "slip-10": ("cKySi8KuPl8", "photo-1750064159040-c37883f82014", "MANITO SILK", "manitosilk_official"),
    "linendress-0": ("dziVRZYOFpI", "photo-1747396206869-75ea57b325ce", "Reistor", "reistor"),
    "linendress-2": ("6LZuSzSwso0", "photo-1504051771394-dd2e66b2e08f", "Icons8 Team", "icons8"),
    "knitdress-12": ("6XE8vz4bD5Q", "photo-1696536451887-9825b5d689aa", "Iryna Studenets", "rudnrina"),
    "knitdress-8": ("FplK_1Z7798", "photo-1759229874810-26aa9a3dda92", "MANITO SILK", "manitosilk_official"),
    "blackdress-6": ("LXbiomJ6who", "photo-1668028554553-f83cac89ce0f", "Redd Francisco", "reddfrancisco"),
    "blackdress-3": ("75tVklPmTiA", "photo-1612872217406-ed2471abf0a0", "Süheyl Burak", "suheylburak"),
    "wsweater-3": ("KlkfFwXXbXc", "photo-1629580626780-7fe7fb0523e9", "Alessia Marusova", "sherry_terry"),
    "wsweater-0": ("mU88MlEFcoU", "photo-1574201635302-388dd92a4c3f", "Valna Studio", "valnastudio"),
    "wsweater-6": ("4vZEDN9qHzA", "photo-1604573824419-289a9a10672c", "Serafima Lazarenko", "sera_fima"),
    "wsweater-9": ("PMVYSAtLlLE", "photo-1634653131107-ecc30d4501ac", "Kateryna Hliznitsova", "kate_gliz"),
    "wturtle-0": ("x0c6vTO5ibA", "photo-1581403341630-a6e0b9d2d257", "Andrey Zvyagintsev", "zvandrei"),
    "wturtle-13": ("z9XO4vU3XJ0", "photo-1785798456504-ef4b435b866f", "Yaroslava Holiachenko", "yara_gr"),
    "wturtle-21": ("tXh8IUQT1D4", "photo-1752486268414-39ca91421479", "ZEELOOL Glasses", "zeelool_official"),
    "wturtle-20": ("BqvCQjoxMHw", "photo-1760552069049-600f71fa5bbf", "amin naderloei", "aminnaderloei"),
    "wshirt-11": ("_KUKzVutxBk", "photo-1548534796-12615d80396c", "Juli Kosolapova", "yuli_superson"),
    "wshirt-2": ("nBDb1m-_nJA", "photo-1543872981-578a0310c83a", "the Bialons", "bialons"),
    "blouse-9": ("09iQ8pafMXU", "photo-1675379086716-95bf8a4d22f2", "Quartier Libre Paris", "quartierlibreparis"),
    "blouse-12": ("zCZBhi4vWTc", "photo-1718278864821-aad0a8f4af4f", "sombre", "light_some_candles"),
    "blouse-10": ("ChOcB6XvBKI", "photo-1655203091785-9b07e64e4459", "Minh Dang", "dangminh97"),
    "blouse-8": ("2jK5PeQmDsY", "photo-1718278867451-0af1bcb0dfc5", "sombre", "light_some_candles"),
    "wtrousers-21": ("J7k1iz__sHw", "photo-1741605037045-516447152dfa", "Sergey Sokolov", "svsokolov"),
    "wtrousers-15": ("3WUEXvBHD-Y", "photo-1595331187203-594837c3c13c", "Eugenia Pan'kiv", "eugenivy_now"),
    "skirt-18": ("uOAZfvoOiIs", "photo-1684685833969-64a080d71aaf", "Adam Blunt", "jayee"),
    "skirt-2": ("NA972Mx7fu0", "photo-1573638687899-e2758e4a373f", "Levin Anton", "levyphoto"),
    "wjeans-0": ("2s3GhhJz2uY", "photo-1598554747436-c9293d6a588f", "KAi'S PHOTOGRAPHY", "kaigabriel42"),
    "wjeans-2": ("nC4-PXzKZcI", "photo-1754555009601-498e9873197e", "Pesce Huang", "pesce"),
    "camelcoat-0": ("zkHv9pvrE9U", "photo-1539533113208-f6df8cc8b543", "Bundo Kim", "bundo"),
    "camelcoat-12": ("euORuc7hHYE", "photo-1635097247472-dfc3e652db97", "Eugenia Pan'kiv", "eugenivy_now"),
    "trench-1": ("NsvkoCYpgog", "photo-1651491646869-3f18f4d30be0", "Phindi H", "glambaeofficial"),
    "trench-7": ("C1MRmjaASc4", "photo-1723390926441-5840f12432fc", "Vadim Berg", "bergvadi"),
    "blazer-21": ("AMI9_G61hq0", "photo-1747817330505-20c1ac06b5b3", "Alina Matveycheva", "alinamatveycheva"),
    "blazer-10": ("2UyY8ix-Dxg", "photo-1747817330508-315506ed9487", "Alina Matveycheva", "alinamatveycheva"),
    "msweater-20": ("Ml8nH8V1J5U", "photo-1711024536430-621af5ddcb67", "Gabriel Martin", "diseniatica"),
    "msweater-4": ("NA9dtyWAFV4", "photo-1611312449297-a69dc9c3987b", "Caio Coelho", "smokthebikini"),
    "msweater-19": ("jaQTN9X98wA", "photo-1771092358890-0db24db44e56", "Devin Santiago", "ydcphotography"),
    "msweater-9": ("-2qhXcmJzOM", "photo-1614495039268-aa9a80429b66", "HamZa NOUASRIA", "hamza01nsr"),
    "mturtle-3": ("mXu1SpzHq6w", "photo-1516914943479-89db7d9ae7f2", "Jeremie Aubut", "jeaubut"),
    "mturtle-14": ("d-FYFOd7XEA", "photo-1789141732594-207d0e61cdf8", "ALIREZA Pandkhahi", "kroba313"),
    "oxford-4": ("F3um9jkcCZY", "photo-1604695573706-53170668f6a6", "Ihor Rapita", "rapitaihor"),
    "oxford-23": ("HGqPrIJAOBY", "photo-1732605559386-bc59426d1b16", "Neakasa", "neakasa"),
    "mlinen-4": ("D_Y-BuWJvjw", "photo-1627686011747-74adda3d2343", "Ricardo Morales", "ricardoaaron"),
    "mlinen-1": ("S4f4apZd-hA", "photo-1713881587420-113c1c43e28a", "tian dayong", "tonnnyj"),
    "mlinen-9": ("B7AXGc58Epk", "photo-1782329993439-6bc0cc7bc7bf", "Ramy Mamdouh", "romba100"),
    "mlinen-0": ("vcTKFYNZop4", "photo-1740711152088-88a009e877bb", "Robert Richman", "linenese_lifestyle"),
    "overshirt-22": ("HUALZppg16k", "photo-1655742260938-82ab000acc2d", "Elisa Photography", "elisamoldovan"),
    "overshirt-13": ("L9rgy8tscsQ", "photo-1719418730257-a9da9282da37", "Salah Regouane", "salaheregouane"),
    "overshirt-6": ("argkg3fGZ2Q", "photo-1668603145969-26173ef4e895", "Mesut çiçen", "mesutcicen"),
    "overshirt-0": ("TzOFHGBBKcU", "photo-1586689311267-e88bb0509995", "Thanos Pal", "thanospal"),
    "mtrousers-10": ("eGoDzmxOOW8", "photo-1656600277220-fe7de4e9453c", "Armin Karami", "arminkarami"),
    "mtrousers-4": ("xbZdXJ4MFzg", "photo-1619470148547-0adbfc64b595", "Vlady Nykulyak", "vlad_nyk95"),
    "mjeans-17": ("aO5KpUZ8bSc", "photo-1714143164139-8fdc14bf3054", "TuanAnh Blue", "blueeyeaa"),
    "mjeans-10": ("M-NPViXH_do", "photo-1611007724518-5baaa6e24ce5", "engin akyurt", "enginakyurt"),
    "chore-14": ("tZhgzjYnGxQ", "photo-1714151676641-7be90ec47f09", "Musa Ortaç", "musaortac"),
    "camelcoat-3": ("iIjResyhhW0", "photo-1619603364904-c0498317e145", "Taras Chernus", "chernus_tr"),
    "camelcoat-8": ("-au3XMzfhro", "photo-1619603364937-8d7af41ef206", "Taras Chernus", "chernus_tr"),
    "overcoat-13": ("PFTjVsYUWzs", "photo-1732842430197-0ecd55fe98ea", "GlassesShop", "glassesshop_9"),
    "overcoat-16": ("rlqU2nuEbJQ", "photo-1737508945707-ebdccee97cc5", "GlassesShop", "glassesshop_9"),
    "suede-2": ("Tuo0DPsglnU", "photo-1641943632479-3798ef1e14c6", "Mahdi Rafiee", "mahdi_rafi_e"),
    "suede-4": ("d2WqpviVzxM", "photo-1610904496878-9b7d5799e3ff", "David Suarez", "davidprspctive"),
    "wshirt-3": ("3ZVlU7xF0PM", "photo-1663573688915-c45fb3b45bba", "Mediamodifier", "mediamodifier"),
    "tee-0": ("7WE1LbSc4zM", "photo-1574180566232-aaad1b5b8450", "Brando Makes Branding", "brandomakesbranding"),
    "polo-11": ("BA8ERqWD4SE", "photo-1767164521355-855b4502abc1", "Babak Eshaghian", "babak22ir"),
    "polo-22": ("hZlTU_ViPCs", "photo-1761956255479-484d7d4fe68a", "Les Taylor", "les_photograph"),
    "tote-0": ("XwjrPFW7xw0", "photo-1624687943971-e86af76d57de", "Ugluk Potroshitel", "uglug"),
    "tote-19": ("KM4O12CDWso", "photo-1780436935760-bf92c364776a", "LOGAN WEAVER | @LGNWVR", "lgnwvr"),
    "tote-2": ("6Rh4vvSaiSg", "photo-1732963947955-858ad7d5e540", "Simply Mersah", "simplymersah"),
    "crossbody-3": ("34mc9TqRznQ", "photo-1718622795525-2295971921ba", "PROBAG FACTORY", "probagfactory"),
    "crossbody-19": ("FYWNzQnXgsk", "photo-1786872814428-1f0d8d685217", "Volodymyr Kozhevnikov", "vkozhevnikov"),
    "crossbody-18": ("4NVpQDko9vA", "photo-1765114459508-2666016760af", "Solace Leather", "solaceleather"),
    "weekender-16": ("7UtUF2esMhQ", "photo-1722263433558-39e32afec072", "Sherif Salem", "sherifsalim1"),
    "weekender-2": ("M0g1sV4SEdo", "photo-1535120927584-0230f40fc1e2", "Jan de Keijzer", "woeiman"),
    "loafers-5": ("xPpfEQe0ZiY", "photo-1777987601447-266e128de448", "Husien Bisky", "husien_bisky1"),
    "loafers-6": ("NySU2CFS9Eo", "photo-1760616172899-0681b97a2de3", "taha siddiqui", "xxtahaxx"),
    "chelsea-0": ("miNo_SFAcws", "photo-1608629601270-a0007becead3", "Noah Smith", "noahsmith"),
    "chelsea-1": ("VbF2tQsjhOM", "photo-1710338514013-42de2bbc36d6", "Rydale Clothing", "rydaleclothing"),
    "chelsea-9": ("AwhukWqsfSs", "photo-1777987601677-3059be0e1388", "Husien Bisky", "husien_bisky1"),
    "chelsea-7": ("ju-B5nlGXzE", "photo-1777987601423-f350ac29b3e9", "Husien Bisky", "husien_bisky1"),
    "sneakers-2": ("jc0o2j7T5LA", "photo-1608379743498-ac08f6d022ba", "The DK Photography", "deepain108"),
    "sneakers-1": ("PUw24-taMKc", "photo-1620989928625-08536e746255", "Ervan M Wirawan", "ervan_me"),
    "mules-1": ("kG7OFwBK8z4", "photo-1718365837137-13cbd931068a", "Virginia Marinova", "virginiaphotostories"),
    "mules-6": ("7QgqCICbgHI", "photo-1718365839003-b76ab753c61e", "Virginia Marinova", "virginiaphotostories"),
    "wscarf-18": ("7MJKlYg6Tc8", "photo-1737061556932-f4930f59b8d0", "Maria Kovalets", "marylooo"),
    "wscarf-19": ("bymqYoPh76Y", "photo-1737063206436-85afbf50e018", "Maria Kovalets", "marylooo"),
    "wscarf-20": ("SXck496Sg54", "photo-1637820578444-ea7333b64a31", "Sergey Sokolov", "svsokolov"),
    "wscarf-22": ("RgEaD36YYGI", "photo-1737053595816-73f1b519a82c", "Maria Kovalets", "marylooo"),
    "hat-19": ("4_IIAJfoMQI", "photo-1591132343561-a204669e59d7", "Brandon Russell", "brandonrussell"),
    "hat-11": ("-xOrRBn02XI", "photo-1674433859621-979ae6e39c1a", "Brandon Zacharias", "brandonzchrs"),
    "belt-2": ("tRu15nFN3Pw", "photo-1666723043169-22e29545675c", "Muhammet SAIN", "kaviaq"),
    "belt-23": ("nUKN8Zat5dA", "photo-1623393807193-e095f7944161", "Gabrielle Henderson", "gabriellefaithhenderson"),
    "silkscarf-20": ("XJJRjzkYTiY", "photo-1777795530497-205664bbd965", "Branislav Rodman", "branislavrodman"),
    "silkscarf-23": ("9dY6seXaLx4", "photo-1777795530530-7823b2913e68", "Branislav Rodman", "branislavrodman"),
    "earrings-18": ("DRbPrVTyTyA", "photo-1632525230528-ec17c49bc168", "JESUS ECA", "jesus_eca"),
    "earrings-0": ("s9idT2PQUt4", "photo-1671644730555-916aa8d8157f", "Ruan Richard Rodrigues", "ricdeoliveira"),
    "earrings-11": ("EO_5VqM03IA", "photo-1614674688981-afa9d1a291ef", "Mykola Kolya Korzh", "kolyakorzh"),
    "earrings-9": ("0UWgtExam8g", "photo-1614674689010-fd47f4299bf6", "Mykola Kolya Korzh", "kolyakorzh"),
    "ed1-7": ("h8fJcfaARJg", "photo-1779406165962-7df12de281b1", "ola szkolda", "olaszkolda"),
    "ed1-6": ("2l4hIRNA5H8", "photo-1779406167603-d0afe0a4cdd7", "ola szkolda", "olaszkolda"),
    "ed1-15": ("2O2cXJemDmo", "photo-1762605135012-56a59a059e60", "Mina Rad", "miinrad"),
    "ed1-21": ("SS1Oldoervo", "photo-1772714601004-23b94ae3913d", "Sẹ́gun Toríọlá", "seguntoriola"),
    "ed6-17": ("9cxiJMMUJZ4", "photo-1646270968802-6bad28659329", "Meg MacDonald", "missmeg_mac"),
    "ed6-0": ("Ds4TsdS095U", "photo-1601379327928-bedfaf9da2d0", "Tijana Drndarski", "izgubljenausvemiru"),
    "ed7-3": ("2NDtPNiLcD0", "photo-1634665810235-011d663754e7", "Kateryna Hliznitsova", "kate_gliz"),
    "ed2-9": ("A2M4F2Ryk10", "photo-1769107805528-964f4de0e342", "Caroline Badran", "___atmos"),
    "ed2-0": ("Apw4z0D9xVE", "photo-1769107805465-bfd41863f1a0", "Caroline Badran", "___atmos"),
    "ed10-9": ("v8JtKauvvDk", "photo-1626784579980-db39c1a13aa9", "lucas Favre", "we_are_rising"),
    "ed10-8": ("5zg-ZDesJAk", "photo-1745847655362-fc86d76584b2", "alex jhonson", "alexjhonson23e"),
    "ed8-7": ("UWUlKFicthA", "photo-1637325262485-5cf1abb98c05", "Teslariu Mihai", "mihaiteslariu0"),
    "ed4-15": ("jN6BqIb-opc", "photo-1764179690401-b7032ffaf7b1", "amin naderloei", "aminnaderloei"),
    "ed5-2": ("iIjResyhhW0", "photo-1619603364904-c0498317e145", "Taras Chernus", "chernus_tr"),
    "cardigan-11": ("6mfBuNAC-g0", "photo-1759229875274-bd920070ceef", "MANITO SILK", "manitosilk_official"),
    "ed6-20": ("5MtJ_fsAR2s", "photo-1633943934209-31b7f3775fee", "Kateryna Hliznitsova", "kate_gliz"),
}

STORE = {
    "name": "Halden",
    "tagline": "Clothes made slowly, to be worn for years.",
    "address": "1 Example Street",
    "city": "Sampletown",
    "postal_code": "00000",
    "country": "IT",
    "email": "hello@example.com",
    "phone": "+00 000 000 0000",
    "opening_hours": "Tuesday to Saturday 10:00 to 19:00, Sunday 11:00 to 17:00",
    "timezone": "Europe/Rome",
    "currency": "EUR",
    "free_shipping_over": "150.00",
    "return_window_days": "30",
}

CATEGORIES = [
    ("dresses", "Dresses"),
    ("knitwear", "Knitwear"),
    ("shirts", "Shirts and blouses"),
    ("tops", "T-shirts and polos"),
    ("trousers", "Trousers and skirts"),
    ("denim", "Denim"),
    ("outerwear", "Coats and jackets"),
    ("shoes", "Shoes"),
    ("bags", "Bags"),
    ("accessories", "Scarves, hats and belts"),
    ("jewellery", "Jewellery"),
]

COLOURS = {
    "black": ("Black", "#1d1c1a"),
    "white": ("White", "#f7f5f0"),
    "ivory": ("Ivory", "#f1ebdf"),
    "ecru": ("Ecru", "#e7dfcd"),
    "cream": ("Cream", "#eee4cf"),
    "champagne": ("Champagne", "#d8c4a2"),
    "oat": ("Oat", "#d9cdb5"),
    "oatmeal": ("Oatmeal", "#cdbfa6"),
    "sand": ("Sand", "#d4c09c"),
    "stone": ("Stone", "#c5baa6"),
    "camel": ("Camel", "#b8895a"),
    "tan": ("Tan", "#b27c4b"),
    "cognac": ("Cognac", "#94552b"),
    "tobacco": ("Tobacco", "#86582f"),
    "chestnut": ("Chestnut", "#6b3d22"),
    "dark-brown": ("Dark brown", "#47301f"),
    "ochre": ("Ochre", "#bd8a3b"),
    "oxblood": ("Oxblood", "#5c2229"),
    "olive": ("Olive", "#66663f"),
    "dove-grey": ("Dove grey", "#b8b4ad"),
    "grey-melange": ("Grey melange", "#9b9a97"),
    "charcoal": ("Charcoal", "#3b3b3d"),
    "navy": ("Navy", "#222d45"),
    "indigo": ("Indigo", "#2b3858"),
    "mid-blue": ("Mid blue", "#6c87a6"),
    "pale-blue": ("Pale blue", "#b6c9df"),
    "chambray": ("Chambray", "#7b91ad"),
    "gold": ("Gold", "#c8a25a"),
    "print": ("Print", "#b48a6c"),
}

LETTERS = ["xs", "s", "m", "l", "xl"]
WOMEN_SHOES = [f"eu-{n}" for n in range(36, 42)]
MEN_SHOES = [f"eu-{n}" for n in range(40, 46)]
ALL_SHOES = [f"eu-{n}" for n in range(36, 46)]
ONE = ["one-size"]

SHIPPING = [
    ("standard", "Standard delivery", "Tracked, free on orders over the free shipping amount", "6.00", True, 3, 5),
    ("express", "Express delivery", "Tracked, next working day when ordered before 2pm", "15.00", False, 1, 2),
    ("pickup", "Collect in store", "Ready in two hours at the Halden store", "0.00", False, 0, 1),
]

WOOL_CARE = "Hand wash cold or dry clean. Dry flat."
COTTON_CARE = "Machine wash at 30°C. Do not tumble dry."
LINEN_CARE = "Machine wash at 30°C. Iron while damp."
SILK_CARE = "Dry clean, or hand wash cold with a silk detergent."
LEATHER_CARE = "Wipe with a dry cloth. Feed with leather balm twice a year."

# Each product: slug, name, department, category, price, old price, new, popularity, days since added,
# colours (the first is the one photographed), sizes, composition, care, description, details,
# images (photo alias, colour or None, alt text), collections.
PRODUCTS = [
    # Women
    dict(
        slug="bias-cut-silk-slip-dress", name="Bias-Cut Silk Slip Dress", department="women", category="dresses",
        price="245.00", old=None, new=True, popularity=96, added=6, colours=["champagne", "black"], sizes=LETTERS,
        composition="100% mulberry silk satin", care=SILK_CARE,
        description="Cut on the bias so the satin falls close to the body without clinging. Fine adjustable straps, a cowl that sits just below the collarbone and a hem that brushes the ankle.",
        details=["Cut on the bias", "Adjustable straps", "Ankle length", "Unlined"],
        images=[("slip-8", "champagne", "Model in a long champagne silk slip dress in a sunlit corridor"), ("slip-10", "champagne", "Close view of a champagne silk slip dress with fine straps")],
        collections=["linen-and-light"],
    ),
    dict(
        slug="linen-shift-dress", name="Linen Shift Dress", department="women", category="dresses",
        price="165.00", old=None, new=False, popularity=71, added=40, colours=["oat", "black"], sizes=LETTERS,
        composition="100% European linen", care=LINEN_CARE,
        description="A sleeveless shift in washed linen that softens with every wear. Straight through the body, with a wide neckline and side seam pockets.",
        details=["Relaxed, straight fit", "Side seam pockets", "Knee length", "Garment washed"],
        images=[("linendress-0", "oat", "Model in a sleeveless oat linen shift dress against a pale wall")],
        collections=["linen-and-light"],
    ),
    dict(
        slug="linen-wrap-dress", name="Linen Wrap Dress", department="women", category="dresses",
        price="185.00", old="230.00", new=False, popularity=64, added=75, colours=["dove-grey"], sizes=LETTERS,
        composition="100% European linen", care=LINEN_CARE,
        description="A long-sleeved wrap dress in fine dove grey linen, tied at the waist with a self belt. Calm, easy and made for warm evenings.",
        details=["Wrap front with self tie", "Long sleeves", "Midi length"],
        images=[("linendress-2", "dove-grey", "Model in profile wearing a long grey linen wrap dress, holding dried grasses")],
        collections=["linen-and-light"],
    ),
    dict(
        slug="rib-knit-midi-dress", name="Rib-Knit Midi Dress", department="women", category="dresses",
        price="195.00", old=None, new=True, popularity=83, added=9, colours=["ecru", "black"], sizes=LETTERS,
        composition="70% merino wool, 30% cashmere", care=WOOL_CARE,
        description="A fine rib that follows the body and stretches with it. Long sleeves, a crew neck and a hem that stops at mid calf, for days that start at the office and end at dinner.",
        details=["Fine rib knit", "Long sleeves", "Mid-calf length"],
        images=[("knitdress-12", "ecru", "Model leaning on a black panel in an ecru long knit dress"), ("knitdress-8", "black", "Model in a black fine-knit dress against a wooden wall")],
        collections=["the-quiet-season"],
    ),
    dict(
        slug="column-evening-dress", name="Column Evening Dress", department="women", category="dresses",
        price="295.00", old=None, new=False, popularity=58, added=60, colours=["black"], sizes=LETTERS,
        composition="Triacetate and polyester crepe", care="Dry clean only.",
        description="A long black column with gathered sleeves and a high round neck. Nothing to add except earrings.",
        details=["Floor length", "Gathered long sleeves", "Concealed back zip"],
        images=[("blackdress-6", "black", "Model seated in a long black dress holding white flowers"), ("blackdress-3", "black", "Model in a black wrap dress by a window")],
        collections=["the-tailoring-edit"],
    ),
    dict(
        slug="chunky-rib-sweater", name="Chunky Rib Sweater", department="women", category="knitwear",
        price="175.00", old=None, new=True, popularity=90, added=4, colours=["ecru", "oatmeal"], sizes=LETTERS,
        composition="100% undyed wool", care=WOOL_CARE,
        description="A thick English rib knitted from undyed wool, so the colour is the sheep's own. Dropped shoulders and a slightly cropped body.",
        details=["English rib", "Dropped shoulders", "Slightly cropped"],
        images=[("wsweater-3", "ecru", "Model against a blue sky in a chunky ecru rib sweater"), ("wsweater-0", "ecru", "Ecru rib sweater pulled over the head against a white wall")],
        collections=["the-quiet-season"],
    ),
    dict(
        slug="cashmere-crewneck", name="Cashmere Crewneck", department="women", category="knitwear",
        price="225.00", old=None, new=False, popularity=94, added=120, colours=["oatmeal", "ochre", "camel"], sizes=LETTERS,
        composition="100% Mongolian cashmere, 2-ply", care=WOOL_CARE,
        description="Two-ply cashmere with a relaxed body and narrow ribbed cuffs. Light enough under a coat, warm enough on its own.",
        details=["2-ply cashmere", "Relaxed fit", "Ribbed cuffs and hem"],
        images=[("wsweater-6", "oatmeal", "Close view of an oatmeal cashmere crewneck in a field"), ("wsweater-9", None, "Folded cashmere sweaters in cream, ochre and camel")],
        collections=["the-quiet-season", "everyday-essentials"],
    ),
    dict(
        slug="fine-merino-turtleneck", name="Fine Merino Turtleneck", department="women", category="knitwear",
        price="125.00", old=None, new=False, popularity=88, added=150, colours=["black", "ivory"], sizes=LETTERS,
        composition="100% extra-fine merino wool", care=WOOL_CARE,
        description="A close-fitting turtleneck in extra-fine merino: the base layer of a winter wardrobe, under tailoring or on its own.",
        details=["Slim fit", "Double-layer collar", "Extra-fine 18.5 micron merino"],
        images=[("wturtle-0", "black", "Model in a black fine merino turtleneck by a colonnade"), ("wturtle-13", "ivory", "Model seated in an ivory turtleneck and black skirt")],
        collections=["everyday-essentials", "the-quiet-season"],
    ),
    dict(
        slug="roll-neck-sweater", name="Roll-Neck Sweater", department="women", category="knitwear",
        price="165.00", old="210.00", new=False, popularity=62, added=200, colours=["camel"], sizes=LETTERS,
        composition="80% lambswool, 20% alpaca", care=WOOL_CARE,
        description="A generous roll neck in lambswool and alpaca, oversized through the body and the sleeves.",
        details=["Oversized fit", "Deep roll neck", "Brushed finish"],
        images=[("wturtle-21", "camel", "Smiling model in a camel roll-neck sweater and sunglasses"), ("wturtle-20", "camel", "Model in a soft camel roll neck in front of bookshelves")],
        collections=["the-quiet-season"],
    ),
    dict(
        slug="poplin-shirt", name="Poplin Shirt", department="women", category="shirts",
        price="110.00", old=None, new=False, popularity=80, added=180, colours=["white"], sizes=LETTERS,
        composition="100% organic cotton poplin", care=COTTON_CARE,
        description="A crisp, slightly oversized shirt in organic cotton poplin, with a long back and a soft collar that also looks right open.",
        details=["Oversized fit", "Longer back hem", "Mother-of-pearl buttons"],
        images=[("wshirt-11", "white", "Black and white portrait of a model in an open white poplin shirt"), ("wshirt-2", "white", "Close view of a white shirt sleeve next to an olive branch")],
        collections=["linen-and-light", "everyday-essentials"],
    ),
    dict(
        slug="silk-crepe-blouse", name="Silk Crepe Blouse", department="women", category="shirts",
        price="189.00", old=None, new=True, popularity=74, added=12, colours=["ivory"], sizes=LETTERS,
        composition="100% silk crepe de chine", care=SILK_CARE,
        description="A V-neck blouse in silk crepe with loose short sleeves and covered buttons. It moves when you do.",
        details=["V neck", "Covered buttons", "Loose fit"],
        images=[("blouse-9", "ivory", "Model in an ivory silk crepe blouse against a white background"), ("blouse-12", "ivory", "Detail of pleats and ruffled cuff on an ivory blouse")],
        collections=["the-tailoring-edit"],
    ),
    dict(
        slug="satin-shirt", name="Satin Shirt", department="women", category="shirts",
        price="159.00", old="199.00", new=False, popularity=55, added=95, colours=["champagne"], sizes=LETTERS,
        composition="Viscose satin", care="Hand wash cold. Iron on the reverse.",
        description="A long, fluid shirt in champagne satin with a classic collar. Wear it tucked into trousers or loose over a slip.",
        details=["Fluid satin", "Classic collar", "Long cuffs"],
        images=[("blouse-10", "champagne", "Model in a long champagne satin shirt in a white studio"), ("blouse-8", "champagne", "Detail of a champagne satin shirt with ruffled cuff")],
        collections=[],
    ),
    dict(
        slug="pleated-wide-leg-trousers", name="Pleated Wide-Leg Trousers", department="women", category="trousers",
        price="175.00", old=None, new=False, popularity=85, added=70, colours=["stone"], sizes=LETTERS,
        composition="Wool and viscose twill", care="Dry clean.",
        description="High-waisted trousers with double pleats and a wide, straight leg that breaks on the shoe.",
        details=["High waist", "Double front pleats", "Side and back pockets"],
        images=[("wtrousers-21", "stone", "Model seated on a stool in stone pleated trousers and a white shirt"), ("wtrousers-15", "stone", "Model in stone wide-leg trousers and a white blouse outdoors")],
        collections=["the-tailoring-edit"],
    ),
    dict(
        slug="pleated-midi-skirt", name="Pleated Midi Skirt", department="women", category="trousers",
        price="145.00", old=None, new=False, popularity=60, added=110, colours=["grey-melange", "stone"], sizes=LETTERS,
        composition="Recycled polyester", care="Machine wash cold. Hang to dry: the pleats come back by themselves.",
        description="Knife pleats that swing as you walk, set on a narrow elastic waistband.",
        details=["Permanent knife pleats", "Elastic waistband", "Midi length"],
        images=[("skirt-18", "grey-melange", "Grey pleated midi skirt in motion"), ("skirt-2", "stone", "Model sitting on a bench in a taupe pleated skirt")],
        collections=[],
    ),
    dict(
        slug="straight-leg-jeans", name="Straight-Leg Jeans", department="women", category="denim",
        price="135.00", old=None, new=False, popularity=87, added=210, colours=["mid-blue"], sizes=LETTERS,
        composition="100% organic cotton denim, 13 oz", care="Wash inside out at 30°C, rarely.",
        description="A high rise and a straight leg cut long, to wear turned up once. Rigid denim that shapes to you within a few wears.",
        details=["High rise", "Straight leg", "Rigid 13 oz denim", "Button fly"],
        images=[("wjeans-0", "mid-blue", "Model in mid-blue straight-leg jeans, one foot on a white chair"), ("wjeans-2", "mid-blue", "Mid-blue straight jeans hanging on a rail")],
        collections=["everyday-essentials"],
    ),
    dict(
        slug="belted-wool-coat", name="Belted Wool Coat", department="women", category="outerwear",
        price="395.00", old=None, new=True, popularity=92, added=3, colours=["camel"], sizes=LETTERS,
        composition="90% wool, 10% cashmere", care="Dry clean.",
        description="A wrap coat in double-faced wool and cashmere, with no lining and no buttons: just a belt and deep patch pockets.",
        details=["Double-faced, unlined", "Self belt", "Patch pockets", "Below-the-knee length"],
        images=[("camelcoat-0", "camel", "Model in a belted camel wool coat against a stone wall"), ("camelcoat-12", "camel", "Detail of a camel wool coat pocket and sleeve")],
        collections=["the-quiet-season", "the-tailoring-edit"],
    ),
    dict(
        slug="classic-trench", name="Classic Trench", department="women", category="outerwear",
        price="345.00", old=None, new=False, popularity=82, added=160, colours=["sand"], sizes=LETTERS,
        composition="Water-repellent cotton gabardine", care="Dry clean.",
        description="The trench as it should be: double-breasted, storm flap, belted cuffs and a gabardine that shrugs off rain.",
        details=["Double-breasted", "Storm flap and belted cuffs", "Water-repellent"],
        images=[("trench-1", "sand", "Smiling model in a sand trench coat holding a small black bag"), ("trench-7", "sand", "Model in a light trench coat in a dark bar")],
        collections=["the-tailoring-edit"],
    ),
    dict(
        slug="oversized-blazer", name="Oversized Blazer", department="women", category="outerwear",
        price="265.00", old=None, new=False, popularity=79, added=85, colours=["sand"], sizes=LETTERS,
        composition="Wool blend twill, viscose lining", care="Dry clean.",
        description="A boxy single-breasted blazer with strong shoulders and a long line. Over a tee, over a dress, over everything.",
        details=["Boxy fit", "Single button", "Fully lined"],
        images=[("blazer-21", "sand", "Model standing in a tiled room in an oversized sand blazer"), ("blazer-10", "sand", "Model in an oversized sand blazer, hands on hips")],
        collections=["the-tailoring-edit"],
    ),
    # Men
    dict(
        slug="cable-knit-crewneck", name="Cable-Knit Crewneck", department="men", category="knitwear",
        price="165.00", old=None, new=False, popularity=77, added=140, colours=["navy"], sizes=LETTERS,
        composition="100% British wool", care=WOOL_CARE,
        description="A traditional cable on a heavy British wool, knitted on old machines and finished by hand at the collar.",
        details=["Traditional cables", "Regular fit", "Hand-linked collar"],
        images=[("msweater-20", "navy", "Man in a navy cable-knit crewneck against a pale wall"), ("msweater-4", "navy", "Navy knit sweater hanging in the dark")],
        collections=["the-quiet-season"],
    ),
    dict(
        slug="merino-crewneck", name="Merino Crewneck", department="men", category="knitwear",
        price="135.00", old=None, new=False, popularity=84, added=230, colours=["black", "charcoal"], sizes=LETTERS,
        composition="100% extra-fine merino wool", care=WOOL_CARE,
        description="A fine gauge crewneck that sits flat under a jacket. The one you will buy twice.",
        details=["Fine gauge", "Regular fit", "Fully fashioned"],
        images=[("msweater-19", "black", "Man in a black merino crewneck and black trousers in a white studio"), ("msweater-9", "charcoal", "Man in a charcoal crewneck turning towards the wall")],
        collections=["everyday-essentials"],
    ),
    dict(
        slug="merino-roll-neck", name="Merino Roll Neck", department="men", category="knitwear",
        price="145.00", old=None, new=True, popularity=73, added=15, colours=["ivory", "black"], sizes=LETTERS,
        composition="100% extra-fine merino wool", care=WOOL_CARE,
        description="A fine roll neck in ivory merino, for under a suit instead of a shirt.",
        details=["Fine gauge", "Slim fit", "Double-layer collar"],
        images=[("mturtle-3", "ivory", "Man in profile in an ivory roll-neck sweater"), ("mturtle-14", "ivory", "Man in a beige suit with an ivory roll neck")],
        collections=["the-tailoring-edit", "the-quiet-season"],
    ),
    dict(
        slug="oxford-shirt", name="Oxford Shirt", department="men", category="shirts",
        price="115.00", old=None, new=False, popularity=86, added=260, colours=["pale-blue", "white"], sizes=LETTERS,
        composition="100% cotton Oxford cloth", care=COTTON_CARE,
        description="A button-down Oxford with a soft roll to the collar and a box pleat at the back.",
        details=["Button-down collar", "Back box pleat", "Regular fit"],
        images=[("oxford-4", "pale-blue", "Man in a pale blue Oxford shirt leaning on a rail"), ("oxford-23", "pale-blue", "Pale blue shirt on a hanger in front of an arch")],
        collections=["everyday-essentials", "the-tailoring-edit"],
    ),
    dict(
        slug="band-collar-linen-shirt", name="Band-Collar Linen Shirt", department="men", category="shirts",
        price="125.00", old=None, new=True, popularity=69, added=20, colours=["ecru"], sizes=LETTERS,
        composition="100% European linen", care=LINEN_CARE,
        description="A collarless shirt in heavy washed linen, with a short placket and a curved hem.",
        details=["Band collar", "Garment washed", "Curved hem"],
        images=[("mlinen-4", "ecru", "Man in an ecru band-collar linen shirt outdoors"), ("mlinen-1", "ecru", "Ecru linen shirt hanging from a branch")],
        collections=["linen-and-light"],
    ),
    dict(
        slug="linen-shirt", name="Linen Shirt", department="men", category="shirts",
        price="120.00", old="150.00", new=False, popularity=66, added=100, colours=["chambray", "indigo"], sizes=LETTERS,
        composition="100% European linen", care=LINEN_CARE,
        description="A classic collar linen shirt in chambray blue, slightly crumpled on purpose.",
        details=["Classic collar", "Chest pocket", "Regular fit"],
        images=[("mlinen-9", "chambray", "Man in a chambray linen shirt in front of mountains"), ("mlinen-0", "indigo", "Indigo linen shirt on a hanger over a white tee")],
        collections=["linen-and-light"],
    ),
    dict(
        slug="wool-overshirt", name="Wool Overshirt", department="men", category="shirts",
        price="215.00", old=None, new=False, popularity=72, added=55, colours=["stone"], sizes=LETTERS,
        composition="Brushed wool blend", care="Dry clean.",
        description="Heavier than a shirt, lighter than a jacket. Two flap pockets and press studs.",
        details=["Brushed wool", "Two chest flap pockets", "Press studs"],
        images=[("overshirt-22", "stone", "Man in a stone wool overshirt over a grey tee"), ("overshirt-13", "stone", "Man in a light grey overshirt in soft light")],
        collections=["the-quiet-season"],
    ),
    dict(
        slug="canvas-overshirt", name="Canvas Overshirt", department="men", category="shirts",
        price="165.00", old=None, new=False, popularity=57, added=170, colours=["ecru"], sizes=LETTERS,
        composition="100% cotton canvas", care=COTTON_CARE,
        description="A washed cotton canvas overshirt with patch pockets, built to fade.",
        details=["Washed canvas", "Patch pockets", "Boxy fit"],
        images=[("overshirt-6", "ecru", "Man in an ecru canvas overshirt in a golden field"), ("overshirt-0", None, "Close view of the collar and buttons of a canvas overshirt")],
        collections=[],
    ),
    dict(
        slug="pleated-wool-trousers", name="Pleated Wool Trousers", department="men", category="trousers",
        price="175.00", old=None, new=False, popularity=70, added=90, colours=["sand"], sizes=LETTERS,
        composition="100% wool tropical", care="Dry clean.",
        description="A single pleat, a high rise and a tapered leg in light tropical wool that travels well.",
        details=["Single pleat", "Side adjusters", "Tapered leg"],
        images=[("mtrousers-10", "sand", "Man in sand pleated trousers and a white tee among rocks"), ("mtrousers-4", "sand", "Detail of the pleat and pocket on sand wool trousers")],
        collections=["the-tailoring-edit"],
    ),
    dict(
        slug="selvedge-straight-jeans", name="Selvedge Straight Jeans", department="men", category="denim",
        price="165.00", old=None, new=False, popularity=81, added=240, colours=["indigo"], sizes=LETTERS,
        composition="100% cotton selvedge denim, 14 oz", care="Wash inside out at 30°C, as rarely as you can.",
        description="Raw indigo selvedge woven on shuttle looms, cut straight. They will fade where you live in them.",
        details=["Raw selvedge denim", "Straight leg", "Copper rivets"],
        images=[("mjeans-17", "indigo", "Folded raw indigo straight jeans on a white table"), ("mjeans-10", "indigo", "Orange stitching on the back pocket of indigo jeans")],
        collections=["everyday-essentials"],
    ),
    dict(
        slug="canvas-chore-jacket", name="Canvas Chore Jacket", department="men", category="outerwear",
        price="225.00", old=None, new=True, popularity=68, added=18, colours=["ecru"], sizes=LETTERS,
        composition="Organic cotton canvas, corduroy collar", care=COTTON_CARE,
        description="The French work jacket, in heavy ecru canvas with three patch pockets.",
        details=["Three patch pockets", "Corozo buttons", "Unlined"],
        images=[("chore-14", "ecru", "Man in an ecru canvas jacket standing near horses")],
        collections=[],
    ),
    dict(
        slug="camel-overcoat", name="Camel Overcoat", department="men", category="outerwear",
        price="445.00", old=None, new=False, popularity=89, added=45, colours=["camel"], sizes=LETTERS,
        composition="80% wool, 20% cashmere", care="Dry clean.",
        description="A single-breasted overcoat with a notch lapel and a straight cut that falls below the knee.",
        details=["Single-breasted", "Below-the-knee length", "Half lined"],
        images=[("camelcoat-3", "camel", "Man in a camel overcoat and roll neck against a beige wall"), ("camelcoat-8", "camel", "Man buttoning a camel overcoat")],
        collections=["the-tailoring-edit", "the-quiet-season"],
    ),
    dict(
        slug="double-breasted-overcoat", name="Double-Breasted Overcoat", department="men", category="outerwear",
        price="495.00", old=None, new=False, popularity=76, added=130, colours=["oatmeal"], sizes=LETTERS,
        composition="Wool and alpaca", care="Dry clean.",
        description="A six-button double-breasted coat in a soft oatmeal wool, with peak lapels and a half belt at the back.",
        details=["Six-button double-breasted", "Peak lapels", "Half belt"],
        images=[("overcoat-13", "oatmeal", "Man in an oatmeal double-breasted overcoat in the street"), ("overcoat-16", "oatmeal", "Man walking in an oatmeal overcoat")],
        collections=["the-tailoring-edit"],
    ),
    dict(
        slug="suede-trucker-jacket", name="Suede Trucker Jacket", department="men", category="outerwear",
        price="545.00", old="620.00", new=False, popularity=67, added=190, colours=["tobacco"], sizes=LETTERS,
        composition="Goat suede, cotton lining", care="Professional leather clean only.",
        description="The trucker jacket in a soft tobacco suede that gets better with age and weather.",
        details=["Soft goat suede", "Chest flap pockets", "Adjustable waist tabs"],
        images=[("suede-2", "tobacco", "Man in a tobacco suede trucker jacket over a dark roll neck"), ("suede-4", "tobacco", "Detail of tobacco suede")],
        collections=[],
    ),
    dict(
        slug="heavyweight-tee", name="Heavyweight Tee", department="unisex", category="tops",
        price="45.00", old=None, new=False, popularity=93, added=300, colours=["white", "black"], sizes=LETTERS,
        composition="100% organic cotton jersey, 240 g", care=COTTON_CARE,
        description="A dense, structured T-shirt that holds its shape wash after wash.",
        details=["240 g jersey", "Regular fit", "Narrow ribbed collar"],
        images=[("wshirt-3", "white", "Model in a plain white heavyweight T-shirt and black trousers on a quiet street")],
        collections=["everyday-essentials", "linen-and-light"],
    ),
    dict(
        slug="knitted-polo", name="Knitted Polo", department="men", category="tops",
        price="125.00", old=None, new=True, popularity=75, added=10, colours=["navy", "camel"], sizes=LETTERS,
        composition="Cotton and silk knit", care=WOOL_CARE,
        description="A short-sleeved polo knitted in a ribbed cotton and silk, open at the collar.",
        details=["Ribbed knit", "Open collar", "Short sleeves"],
        images=[("polo-11", "navy", "Man in a navy knitted polo in a garden"), ("polo-22", "camel", "Man in a camel knitted polo and sunglasses")],
        collections=["linen-and-light"],
    ),
    # Accessories, shoes, jewellery
    dict(
        slug="leather-tote", name="Leather Tote", department="unisex", category="bags",
        price="285.00", old=None, new=False, popularity=91, added=280, colours=["cognac"], sizes=ONE,
        composition="Full-grain vegetable-tanned leather", care=LEATHER_CARE,
        description="A simple unlined tote in vegetable-tanned leather that darkens beautifully. Fits a laptop and a day.",
        details=["Unlined", "Inside pocket", "Fits a 15-inch laptop"],
        images=[("tote-0", "cognac", "Cognac leather tote hanging from a white door"), ("tote-19", "cognac", "Woman carrying a cognac leather tote at a flower market")],
        collections=["everyday-essentials"],
    ),
    dict(
        slug="canvas-market-tote", name="Canvas Market Tote", department="unisex", category="bags",
        price="75.00", old=None, new=False, popularity=63, added=150, colours=["stone"], sizes=ONE,
        composition="Heavy cotton canvas", care="Spot clean.",
        description="A heavy canvas tote for the market and the beach.",
        details=["Heavy canvas", "Long handles"],
        images=[("tote-2", "stone", "Stone canvas tote on a white chair")],
        collections=["linen-and-light"],
    ),
    dict(
        slug="leather-barrel-bag", name="Leather Barrel Bag", department="women", category="bags",
        price="195.00", old=None, new=True, popularity=78, added=8, colours=["cognac", "cream"], sizes=ONE,
        composition="Smooth calf leather", care=LEATHER_CARE,
        description="A small barrel bag on a long adjustable strap, worn across the body.",
        details=["Adjustable strap", "Zip closure", "Small size"],
        images=[("crossbody-3", "cognac", "Cognac leather barrel bag on a marble table"), ("crossbody-19", "cream", "Cream leather barrel bag on a terracotta backdrop")],
        collections=[],
    ),
    dict(
        slug="saddle-bag", name="Saddle Bag", department="women", category="bags",
        price="245.00", old=None, new=False, popularity=65, added=115, colours=["black"], sizes=ONE,
        composition="Smooth calf leather, brass hardware", care=LEATHER_CARE,
        description="A curved saddle bag with a single brass clasp.",
        details=["Brass clasp", "Adjustable strap"],
        images=[("crossbody-18", "black", "Model in a black blazer holding a black leather saddle bag")],
        collections=["the-tailoring-edit"],
    ),
    dict(
        slug="leather-weekender", name="Leather Weekender", department="unisex", category="bags",
        price="395.00", old=None, new=False, popularity=59, added=220, colours=["chestnut"], sizes=ONE,
        composition="Full-grain leather, cotton lining", care=LEATHER_CARE,
        description="A two-night bag in full-grain leather, with a detachable shoulder strap.",
        details=["Detachable strap", "Inner zip pocket", "Cabin size"],
        images=[("weekender-16", "chestnut", "Chestnut leather weekender bag"), ("weekender-2", "chestnut", "Man carrying a tan leather weekender through a garden")],
        collections=[],
    ),
    dict(
        slug="penny-loafers", name="Penny Loafers", department="men", category="shoes",
        price="225.00", old=None, new=False, popularity=80, added=175, colours=["chestnut", "black"], sizes=MEN_SHOES,
        composition="Calf leather, leather sole", care=LEATHER_CARE,
        description="Goodyear-welted penny loafers on a leather sole, ready to be resoled for years.",
        details=["Goodyear welted", "Leather sole", "Made in Italy"],
        images=[("loafers-5", "chestnut", "Chestnut penny loafers on a black stool"), ("loafers-6", "black", "Black loafers worn with black trousers")],
        collections=["the-tailoring-edit"],
    ),
    dict(
        slug="suede-chelsea-boots", name="Suede Chelsea Boots", department="men", category="shoes",
        price="265.00", old=None, new=False, popularity=74, added=125, colours=["tobacco"], sizes=MEN_SHOES,
        composition="Suede upper, rubber sole", care="Brush after wear. Use a suede protector.",
        description="Chelsea boots in a soft tobacco suede on a light crepe-style rubber sole.",
        details=["Elastic side panels", "Pull tab", "Rubber sole"],
        images=[("chelsea-0", "tobacco", "Pair of tobacco suede Chelsea boots"), ("chelsea-1", "tobacco", "Suede Chelsea boots on a pale blue background")],
        collections=["the-quiet-season"],
    ),
    dict(
        slug="leather-chelsea-boots", name="Leather Chelsea Boots", department="women", category="shoes",
        price="285.00", old=None, new=False, popularity=71, added=135, colours=["dark-brown"], sizes=WOMEN_SHOES,
        composition="Calf leather, leather sole", care=LEATHER_CARE,
        description="Slim Chelsea boots in polished dark brown leather.",
        details=["Elastic side panels", "Leather sole", "3 cm heel"],
        images=[("chelsea-9", "dark-brown", "Dark brown leather Chelsea boots"), ("chelsea-7", "dark-brown", "Dark brown Chelsea boots on a piece of wood")],
        collections=["the-quiet-season"],
    ),
    dict(
        slug="minimal-leather-sneakers", name="Minimal Leather Sneakers", department="unisex", category="shoes",
        price="165.00", old=None, new=False, popularity=95, added=290, colours=["white"], sizes=ALL_SHOES,
        composition="Calf leather, rubber cupsole", care="Wipe clean with a damp cloth.",
        description="Clean white leather sneakers with no logos, on a stitched rubber cupsole.",
        details=["Stitched cupsole", "Leather lining", "No logos"],
        images=[("sneakers-2", "white", "Pair of plain white leather sneakers on black")],
        collections=["everyday-essentials"],
    ),
    dict(
        slug="gum-sole-trainers", name="Gum-Sole Trainers", department="unisex", category="shoes",
        price="145.00", old="180.00", new=False, popularity=61, added=160, colours=["white"], sizes=ALL_SHOES,
        composition="Leather and suede, gum rubber sole", care="Wipe clean. Brush the suede.",
        description="Low trainers in white leather and suede panels on a natural gum sole.",
        details=["Suede panels", "Gum rubber sole"],
        images=[("sneakers-1", "white", "Hand holding a white leather and suede trainer with a gum sole")],
        collections=[],
    ),
    dict(
        slug="block-heel-mules", name="Block-Heel Mules", department="women", category="shoes",
        price="185.00", old=None, new=True, popularity=70, added=14, colours=["tan"], sizes=WOMEN_SHOES,
        composition="Nappa leather, leather sole", care=LEATHER_CARE,
        description="Square-toe mules on a 6 cm block heel, with a wide padded strap.",
        details=["6 cm block heel", "Padded strap", "Square toe"],
        images=[("mules-1", "tan", "Tan leather block-heel mules by a white column"), ("mules-6", "tan", "Model wearing tan block-heel mules on stone steps")],
        collections=["linen-and-light"],
    ),
    dict(
        slug="ribbed-wool-scarf", name="Ribbed Wool Scarf", department="unisex", category="accessories",
        price="85.00", old=None, new=False, popularity=64, added=145, colours=["charcoal", "navy"], sizes=ONE,
        composition="100% lambswool", care=WOOL_CARE,
        description="A long ribbed scarf in lambswool, generous enough to wrap twice.",
        details=["Full rib", "200 by 30 cm"],
        images=[("wscarf-18", "charcoal", "Rolled charcoal ribbed wool scarf on wood"), ("wscarf-19", "navy", "Rolled navy ribbed scarf on wood")],
        collections=["the-quiet-season"],
    ),
    dict(
        slug="cashmere-fringe-scarf", name="Cashmere Fringe Scarf", department="unisex", category="accessories",
        price="165.00", old=None, new=False, popularity=68, added=100, colours=["camel", "grey-melange"], sizes=ONE,
        composition="100% cashmere", care=WOOL_CARE,
        description="A light woven cashmere scarf with a hand-twisted fringe.",
        details=["Woven cashmere", "Hand-twisted fringe", "190 by 70 cm"],
        images=[("wscarf-20", "camel", "Folded camel cashmere scarf with fringe"), ("wscarf-22", "grey-melange", "Grey cashmere scarf with a long fringe")],
        collections=["the-quiet-season"],
    ),
    dict(
        slug="ribbed-beanie", name="Ribbed Beanie", department="unisex", category="accessories",
        price="55.00", old=None, new=False, popularity=72, added=120, colours=["camel"], sizes=ONE,
        composition="Merino and cashmere", care=WOOL_CARE,
        description="A deep-cuffed beanie in a soft merino and cashmere rib.",
        details=["Deep cuff", "Fine rib"],
        images=[("hat-19", "camel", "Woman in a camel ribbed beanie in a forest"), ("hat-11", "camel", "Woman seen from behind in a camel beanie in the snow")],
        collections=["the-quiet-season"],
    ),
    dict(
        slug="leather-belt", name="Leather Belt", department="unisex", category="accessories",
        price="79.00", old=None, new=False, popularity=66, added=250, colours=["tan"], sizes=["s", "m", "l"],
        composition="Vegetable-tanned leather, solid brass buckle", care=LEATHER_CARE,
        description="A 3 cm belt in vegetable-tanned leather with a plain brass buckle.",
        details=["3 cm wide", "Solid brass buckle"],
        images=[("belt-2", "tan", "Tan leather belt coiled on a desk"), ("belt-23", "tan", "Tan belt worn with light jeans and a knit")],
        collections=["everyday-essentials"],
    ),
    dict(
        slug="printed-silk-scarf", name="Printed Silk Scarf", department="women", category="accessories",
        price="125.00", old=None, new=True, popularity=60, added=5, colours=["print"], sizes=ONE,
        composition="100% silk twill, hand-rolled edges", care=SILK_CARE,
        description="A silk twill square printed with an archive botanical motif, edges rolled by hand.",
        details=["90 by 90 cm", "Hand-rolled edges"],
        images=[("silkscarf-20", "print", "Printed silk scarf tied around a plaster bust"), ("silkscarf-23", "print", "Printed silk scarf twisted around an orange slice")],
        collections=[],
    ),
    dict(
        slug="gold-huggie-hoops", name="Gold Huggie Hoops", department="women", category="jewellery",
        price="95.00", old=None, new=False, popularity=82, added=200, colours=["gold"], sizes=ONE,
        composition="18k gold vermeil on sterling silver", care="Keep dry. Polish with a soft cloth.",
        description="Small chunky hoops that hug the lobe, for every day.",
        details=["Sold as a pair", "Hinged closure"],
        images=[("earrings-18", "gold", "Pair of gold huggie hoop earrings"), ("earrings-0", "gold", "Gold huggie hoop worn on the ear")],
        collections=["everyday-essentials"],
    ),
    dict(
        slug="dome-ring", name="Dome Ring", department="women", category="jewellery",
        price="110.00", old=None, new=False, popularity=58, added=210, colours=["gold"], sizes=["s", "m", "l"],
        composition="18k gold vermeil on sterling silver", care="Keep dry. Polish with a soft cloth.",
        description="A rounded dome ring with a mirror finish.",
        details=["Mirror polish", "Sizes S (50), M (54), L (58)"],
        images=[("earrings-11", "gold", "Gold dome ring on a pebble"), ("earrings-9", "gold", "Gold dome ring among stones")],
        collections=[],
    ),
]

COLLECTIONS = [
    ("the-quiet-season", "The Quiet Season", "Knits, wool and the first cold mornings",
     "Heavy ribs, brushed wool and coats you can disappear into. Everything here is made to be worn on repeat from October to March.",
     "ed4-15", "Woman in a beige coat on an autumn street"),
    ("linen-and-light", "Linen and Light", "Loose weaves for long days",
     "Washed linen, silk and canvas in the colours of sand and stone, for the months when the evenings stay warm.",
     "ed7-3", "Draped cream linen fabric"),
    ("the-tailoring-edit", "The Tailoring Edit", "Soft shoulders, sharp lines",
     "Blazers, pleated trousers and long coats, cut with room to move.",
     "ed1-21", "Model in a cream suit seated on a white chair against a warm backdrop"),
    ("everyday-essentials", "Everyday Essentials", "The pieces you reach for first",
     "The shirts, knits, denim and leather goods that hold a wardrobe together.",
     "ed6-0", "A stack of folded knitwear in grey and cream"),
]

EDITORIAL = [
    ("home-hero", "Made slowly. Worn for years.",
     "Natural fibres, honest construction and colours that sit together. New pieces for the cold months are in.", "ed1-7",
     "Model in a cream trench and trousers against a warm studio wall"),
    ("home-hero-alt", "", "", "ed1-6", "Model in a cream suit crouching in the studio"),
    ("women", "Women", "Dresses, knitwear, tailoring and coats.", "ed1-15", "Model in a long beige dress in a pale studio"),
    ("men", "Men", "Overcoats, knitwear, shirts and denim.", "ed5-2", "Man in a camel overcoat and roll neck"),
    ("accessories", "Bags, shoes and the rest", "Leather goods made to be repaired, not replaced.", "tote-19",
     "Woman carrying a cognac leather tote at a flower market"),
    ("knitwear", "Knitwear, considered",
     "Our knits come from small mills that spin and knit in the same town. Undyed wool, two-ply cashmere, fine merino: chosen to last more than one winter.",
     "cardigan-11", "Two people in beige knitwear in a wood-panelled room"),
    ("atelier", "From the atelier",
     "Every Halden piece is sampled in our studio before it is made. We cut, wear, wash and wear again, and only then do we order fabric.",
     "ed10-9", "A woman at a sewing machine in a bright studio"),
    ("store", "Visit the store",
     "Try everything on, have trousers hemmed while you wait, or collect an online order two hours after placing it.",
     "ed2-9", "Linen clothes on wooden hangers next to a tall cactus in a bright shop"),
    ("care", "Care for what you own",
     "Wash less, air more, fold knits instead of hanging them. A short guide to making clothes last.", "ed6-20",
     "Folded cream knitwear"),
    ("portrait", "", "", "ed8-7", "Portrait of a woman in a grey turtleneck"),
]


def photo_row(alias: str, photo_ids: dict) -> int:
    """Row id of a photo. Two aliases of the same Unsplash photo share one row."""
    unsplash_id = PHOTOS[alias][0]
    if unsplash_id not in photo_ids:
        photo_ids[unsplash_id] = (len(photo_ids) + 1, alias)
    return photo_ids[unsplash_id][0]


def stock_for(rng: random.Random, size: str, position: int) -> int:
    """Plenty in the middle sizes, little at the edges, and a few sold out or nearly."""
    roll = rng.random()
    if roll < 0.06:
        return 0
    if roll < 0.16:
        return rng.randint(1, 3)
    middle = {"s": 1.2, "m": 1.5, "l": 1.1, "eu-38": 1.3, "eu-39": 1.3, "eu-42": 1.3, "eu-43": 1.2}.get(size, 0.8)
    base = 4 if position == 0 else 2
    return int(rng.randint(base, base + 10) * middle)


def write(name: str, header: list[str], rows: list[list]) -> None:
    with open(DATA / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


def main() -> None:
    rng = random.Random(20261004)
    DATA.mkdir(exist_ok=True)

    sizes = (
        [(code, code.upper(), "letter", i) for i, code in enumerate(LETTERS)]
        + [(f"eu-{n}", str(n), "shoe", n) for n in range(36, 46)]
        + [("one-size", "One size", "one", 0)]
    )
    size_ids = {code: i + 1 for i, (code, *_rest) in enumerate(sizes)}
    category_ids = {slug: i + 1 for i, (slug, _) in enumerate(CATEGORIES)}
    colour_ids = {slug: i + 1 for i, slug in enumerate(COLOURS)}
    photo_ids: dict[str, tuple[int, str]] = {}

    products, images, variants = [], [], []
    for pid, p in enumerate(PRODUCTS, start=1):
        products.append([
            pid, p["slug"], p["name"], p["department"], category_ids[p["category"]], "active", p["description"],
            "|".join(p["details"]), p["composition"], p["care"], p["price"], p["old"] or "", int(p["new"]),
            p["popularity"], p["added"],
        ])
        for position, (alias, colour, alt) in enumerate(p["images"]):
            images.append([len(images) + 1, pid, photo_row(alias, photo_ids), colour_ids[colour] if colour else "", alt, position])
        for ci, colour in enumerate(p["colours"]):
            for size in p["sizes"]:
                sku = f"HD-{pid:03d}-{colour.upper()[:4]}-{size.upper().replace('EU-', '')}"
                variants.append([len(variants) + 1, pid, colour_ids[colour], size_ids[size], sku, stock_for(rng, size, ci)])

    product_ids = {p["slug"]: i for i, p in enumerate(PRODUCTS, start=1)}
    collections = [
        [i, slug, title, subtitle, text, photo_row(alias, photo_ids), alt, i]
        for i, (slug, title, subtitle, text, alias, alt) in enumerate(COLLECTIONS, start=1)
    ]
    collection_ids = {c[1]: c[0] for c in collections}
    links = [
        [collection_ids[c], product_ids[p["slug"]]] for p in PRODUCTS for c in p["collections"]
    ]
    editorial = [
        [i, key, title, text, photo_row(alias, photo_ids), alt] for i, (key, title, text, alias, alt) in enumerate(EDITORIAL, start=1)
    ]

    photos = []
    for pid, alias in sorted(photo_ids.values()):
        unsplash_id, path, name, username = PHOTOS[alias]
        photos.append([pid, UNSPLASH_CDN + path, name, f"https://unsplash.com/@{username}", f"https://unsplash.com/photos/{unsplash_id}"])

    write("store.csv", list(STORE), [list(STORE.values())])
    write("photos.csv", ["id", "url", "photographer", "photographer_url", "source_url"], photos)
    write("editorial.csv", ["id", "key", "title", "text", "photo_id", "alt"], editorial)
    write("categories.csv", ["id", "slug", "name", "position"], [[category_ids[s], s, n, i] for i, (s, n) in enumerate(CATEGORIES)])
    write("colours.csv", ["id", "slug", "name", "hex"], [[colour_ids[s], s, n, h] for s, (n, h) in COLOURS.items()])
    write("sizes.csv", ["id", "code", "label", "system", "position"], [[size_ids[c], c, label, system, pos] for c, label, system, pos in sizes])
    write(
        "shipping_methods.csv",
        ["id", "code", "name", "description", "price", "free_over_threshold", "days_min", "days_max", "position"],
        [[i, *row[:4], int(row[4]), row[5], row[6], i] for i, row in enumerate(SHIPPING, start=1)],
    )
    write(
        "products.csv",
        ["id", "slug", "name", "department", "category_id", "status", "description", "details", "composition", "care",
         "price", "compare_at_price", "is_new", "popularity", "added_days_ago"],
        products,
    )
    write("product_images.csv", ["id", "product_id", "photo_id", "colour_id", "alt", "position"], images)
    write("variants.csv", ["id", "product_id", "colour_id", "size_id", "sku", "stock"], variants)
    write("collections.csv", ["id", "slug", "title", "subtitle", "description", "photo_id", "alt", "position"], collections)
    write("collection_products.csv", ["collection_id", "product_id"], links)


if __name__ == "__main__":
    main()
