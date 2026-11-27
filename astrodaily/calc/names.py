"""English and Hindi names for panchang elements."""

TITHI = [
    ("Pratipada", "प्रतिपदा"), ("Dwitiya", "द्वितीया"), ("Tritiya", "तृतीया"),
    ("Chaturthi", "चतुर्थी"), ("Panchami", "पंचमी"), ("Shashthi", "षष्ठी"),
    ("Saptami", "सप्तमी"), ("Ashtami", "अष्टमी"), ("Navami", "नवमी"),
    ("Dashami", "दशमी"), ("Ekadashi", "एकादशी"), ("Dwadashi", "द्वादशी"),
    ("Trayodashi", "त्रयोदशी"), ("Chaturdashi", "चतुर्दशी"),
]
PURNIMA = ("Purnima", "पूर्णिमा")
AMAVASYA = ("Amavasya", "अमावस्या")

PAKSHA = {"shukla": ("Shukla", "शुक्ल"), "krishna": ("Krishna", "कृष्ण")}

NAKSHATRA = [
    ("Ashwini", "अश्विनी"), ("Bharani", "भरणी"), ("Krittika", "कृत्तिका"),
    ("Rohini", "रोहिणी"), ("Mrigashira", "मृगशिरा"), ("Ardra", "आर्द्रा"),
    ("Punarvasu", "पुनर्वसु"), ("Pushya", "पुष्य"), ("Ashlesha", "आश्लेषा"),
    ("Magha", "मघा"), ("Purva Phalguni", "पूर्वा फाल्गुनी"),
    ("Uttara Phalguni", "उत्तरा फाल्गुनी"), ("Hasta", "हस्त"), ("Chitra", "चित्रा"),
    ("Swati", "स्वाति"), ("Vishakha", "विशाखा"), ("Anuradha", "अनुराधा"),
    ("Jyeshtha", "ज्येष्ठा"), ("Mula", "मूल"), ("Purva Ashadha", "पूर्वाषाढ़ा"),
    ("Uttara Ashadha", "उत्तराषाढ़ा"), ("Shravana", "श्रवण"), ("Dhanishta", "धनिष्ठा"),
    ("Shatabhisha", "शतभिषा"), ("Purva Bhadrapada", "पूर्वभाद्रपदा"),
    ("Uttara Bhadrapada", "उत्तरभाद्रपदा"), ("Revati", "रेवती"),
]

YOGA = [
    ("Vishkambha", "विष्कम्भ"), ("Priti", "प्रीति"), ("Ayushman", "आयुष्मान"),
    ("Saubhagya", "सौभाग्य"), ("Shobhana", "शोभन"), ("Atiganda", "अतिगण्ड"),
    ("Sukarma", "सुकर्मा"), ("Dhriti", "धृति"), ("Shula", "शूल"), ("Ganda", "गण्ड"),
    ("Vriddhi", "वृद्धि"), ("Dhruva", "ध्रुव"), ("Vyaghata", "व्याघात"),
    ("Harshana", "हर्षण"), ("Vajra", "वज्र"), ("Siddhi", "सिद्धि"),
    ("Vyatipata", "व्यतीपात"), ("Variyana", "वरीयान"), ("Parigha", "परिघ"),
    ("Shiva", "शिव"), ("Siddha", "सिद्ध"), ("Sadhya", "साध्य"), ("Shubha", "शुभ"),
    ("Shukla", "शुक्ल"), ("Brahma", "ब्रह्म"), ("Indra", "इन्द्र"),
    ("Vaidhriti", "वैधृति"),
]

# Repeating (movable) karanas, 7 of them, then four fixed ones.
KARANA_MOVABLE = [
    ("Bava", "बव"), ("Balava", "बालव"), ("Kaulava", "कौलव"), ("Taitila", "तैतिल"),
    ("Gara", "गर"), ("Vanija", "वणिज"), ("Vishti (Bhadra)", "विष्टि (भद्रा)"),
]
KARANA_FIXED = {
    0: ("Kimstughna", "किंस्तुघ्न"),
    57: ("Shakuni", "शकुनि"),
    58: ("Chatushpada", "चतुष्पद"),
    59: ("Naga", "नाग"),
}

# Sunday first, matching the choghadiya and Rahu Kaal tables.
VARA = [
    ("Sunday", "रविवार"), ("Monday", "सोमवार"), ("Tuesday", "मंगलवार"),
    ("Wednesday", "बुधवार"), ("Thursday", "गुरुवार"), ("Friday", "शुक्रवार"),
    ("Saturday", "शनिवार"),
]

# Cyclic order of choghadiya names, with nature (good / neutral / bad).
CHOGHADIYA_CYCLE = [
    ("Udveg", "उद्वेग", "bad"), ("Char", "चर", "neutral"), ("Labh", "लाभ", "good"),
    ("Amrit", "अमृत", "good"), ("Kaal", "काल", "bad"), ("Shubh", "शुभ", "good"),
    ("Rog", "रोग", "bad"),
]
# Index in the cycle of the first day slot for each weekday (Sunday first).
CHOGHADIYA_DAY_START = [0, 3, 6, 2, 5, 1, 4]

RAHU_KAAL = ("Rahu Kaal", "राहु काल")
GULIKA = ("Gulika Kaal", "गुलिक काल")
YAMAGANDA = ("Yamaganda", "यमगण्ड")
ABHIJIT = ("Abhijit Muhurat", "अभिजीत मुहूर्त")
