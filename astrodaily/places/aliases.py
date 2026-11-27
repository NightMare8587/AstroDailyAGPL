"""Common Hindi spellings that GeoNames does not carry for major cities.

GeoNames has one or two Hindi names per place and often an older or official form (Bombay, Bangalore, Gurugram), so
people typing the name they actually use ("मुंबई", "बेंगलुरु", "गुड़गांव") found nothing. Each entry is
GeoNames id -> (expected English name, Hindi names). The first Hindi name is shown to people; all of them are
searchable. An entry is applied only when the English name matches, so a wrong id can never rename another place.
"""

ALIASES: dict[int, tuple[str, tuple[str, ...]]] = {
    1275339: ("Mumbai", ("मुंबई", "बम्बई", "मुम्बई", "बॉम्बे")),
    1277333: ("Bengaluru", ("बेंगलुरु", "बेंगलूरु", "बैंगलोर", "बंगलौर")),
    1270642: ("Gurugram", ("गुरुग्राम", "गुड़गांव", "गुड़गाँव")),
    1269743: ("Indore", ("इंदौर",)),
    1254163: ("Thiruvananthapuram", ("तिरुवनंतपुरम", "त्रिवेंद्रम")),
    1275004: ("Kolkata", ("कोलकाता", "कलकत्ता")),
    1264527: ("Chennai", ("चेन्नई", "मद्रास")),
    1253405: ("Varanasi", ("वाराणसी", "बनारस", "काशी")),
    1278994: ("Prayagraj", ("प्रयागराज", "इलाहाबाद")),
    1273874: ("Kochi", ("कोच्चि", "कोचीन")),
    1253573: ("Vadodara", ("वडोदरा", "बड़ौदा")),
    1258526: ("Ranchi", ("रांची", "राँची")),
}
