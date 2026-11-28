"""Names (English and Hindi) for the Ashtakoota match: the eight parts, what each one looks at, and the values."""

PARTS = {
    "varna": (("Varna", "वर्ण"), ("How well your outlooks fit", "आपके नज़रिए कितने मेल खाते हैं")),
    "vashya": (("Vashya", "वश्य"), ("How easily you move each other", "आप एक-दूसरे को कितनी सहजता से प्रभावित करते हैं")),
    "tara": (("Tara", "तारा"), ("How your birth stars get on", "आपके जन्म नक्षत्र कितने सुहाते हैं")),
    "yoni": (("Yoni", "योनि"), ("Physical and intimate ease", "शारीरिक और आत्मीय सहजता")),
    "graha_maitri": (("Graha Maitri", "ग्रह मैत्री"), ("Friendship between your minds", "आपके मन की मित्रता")),
    "gana": (("Gana", "गण"), ("How your temperaments match", "आपके स्वभाव कितने मिलते हैं")),
    "bhakoot": (("Bhakoot", "भकूट"), ("Emotional bond and shared life", "भावनात्मक बंधन और साझा जीवन")),
    "nadi": (("Nadi", "नाड़ी"), ("Health and energy balance", "स्वास्थ्य और ऊर्जा का संतुलन")),
}

VALUES = {
    "Brahmin": ("Brahmin", "ब्राह्मण"), "Kshatriya": ("Kshatriya", "क्षत्रिय"), "Vaishya": ("Vaishya", "वैश्य"),
    "Shudra": ("Shudra", "शूद्र"),
    "Chatushpada": ("Chatushpada", "चतुष्पद"), "Manava": ("Manava", "मानव"), "Jalachara": ("Jalachara", "जलचर"),
    "Vanachara": ("Vanachara", "वनचर"), "Keeta": ("Keeta", "कीट"),
    "Horse": ("Horse", "अश्व"), "Elephant": ("Elephant", "गज"), "Sheep": ("Sheep", "मेष"), "Serpent": ("Serpent", "सर्प"),
    "Dog": ("Dog", "श्वान"), "Cat": ("Cat", "मार्जार"), "Rat": ("Rat", "मूषक"), "Cow": ("Cow", "गौ"),
    "Buffalo": ("Buffalo", "महिष"), "Tiger": ("Tiger", "व्याघ्र"), "Deer": ("Deer", "मृग"), "Monkey": ("Monkey", "वानर"),
    "Mongoose": ("Mongoose", "नकुल"), "Lion": ("Lion", "सिंह"),
    "Deva": ("Deva", "देव"), "Manushya": ("Manushya", "मनुष्य"), "Rakshasa": ("Rakshasa", "राक्षस"),
    "Aadi": ("Aadi", "आदि"), "Madhya": ("Madhya", "मध्य"), "Antya": ("Antya", "अंत्य"),
}

# (lowest total that reaches the band, key, English, Hindi). Kept gentle: no band tells anyone not to marry.
BANDS = (
    (33.0, "great", "A very good match", "बहुत अच्छा मेल"),
    (25.0, "good", "A good match", "अच्छा मेल"),
    (18.0, "fair", "A workable match", "निभाने लायक मेल"),
    (0.0, "low", "A few things to talk through", "कुछ बातें साथ बैठकर समझने की हैं"),
)


def band(total: float) -> tuple[str, str, str]:
    for floor, key, en, hi in BANDS:
        if total >= floor:
            return key, en, hi
    return BANDS[-1][1:]
