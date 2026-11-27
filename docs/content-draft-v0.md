# Content draft v0 (status: DRAFT, nothing here is reviewed)

Samples for the reviewer to react to. Real snippets will live in the private content repo and be imported
into `content_snippets`. Hindi was drafted by a model and **must be read by a native speaker**.
Slots in braces are filled by the engine.

## Tone guide
Calm, practical, one idea per sentence. Say "suits" and "go easy", never "good" or "bad" luck. No fear:
no illness, loss, accident or death. No certainty words ("will", "definitely"). Do not call anything
"ancient" or "classical" until a reviewer approves it. Under 25 words per snippet.

## Lint rules (automated, planned)
Banned: death, disease, accident, curse, doom, "will definitely", "guaranteed". Max 160 characters. Every
snippet has English and Hindi. No duplicate text. Slots must be known names.

## Nakshatra categories (`nakshatra_<category>`)
Slots: `{nakshatra}`.

**Dhruva (fixed)**, do:
- EN: "{nakshatra} is a steady star. Good for laying foundations and commitments meant to last."
- HI: "{nakshatra} एक स्थिर नक्षत्र है। नींव रखने और लंबे समय के संकल्प के लिए अनुकूल।"

**Chara (movable)**, do:
- EN: "A moving star today. Travel, errands and changes of place go smoothly."
- HI: "आज चलायमान नक्षत्र है। यात्रा, काम-काज के चक्कर और बदलाव सहज रहेंगे।"

**Kshipra (swift)**, do:
- EN: "A quick, light star. Start small tasks, trade or learning without delay."
- HI: "आज तेज़ और हल्का नक्षत्र है। छोटे काम, लेन-देन या पढ़ाई बिना देर शुरू करें।"

**Mridu (soft)**, do:
- EN: "A gentle star. Suits art, friendships and soft conversations."
- HI: "कोमल नक्षत्र है। कला, मित्रता और नरम बातचीत के लिए उपयुक्त।"

**Ugra (fierce)**, go easy:
- EN: "A forceful star. Keep to decisive tasks and hold off on fresh, delicate starts."
- HI: "प्रबल नक्षत्र है। निर्णायक काम करें, नाज़ुक नई शुरुआत थोड़ी टालें।"

**Tikshna (sharp)**, go easy:
- EN: "A sharp star. Good for repairs and investigation, less so for new ventures."
- HI: "तीक्ष्ण नक्षत्र है। मरम्मत और जाँच के लिए ठीक, नए उपक्रम के लिए कम।"

**Mishra (mixed)**, info:
- EN: "A mixed star. Balance routine work with careful pacing."
- HI: "मिश्र नक्षत्र है। नियमित काम और सावधान गति के बीच संतुलन रखें।"

## Tithi groups
**Nanda (1, 6, 11)**: EN "A cheerful tithi. Suits celebrations and starting joyful work." /
HI "आनंददायक तिथि। उत्सव और हर्ष के कामों की शुरुआत के लिए उपयुक्त।"
**Bhadra (2, 7, 12)**: EN "A nurturing tithi. Suits health routines and auspicious acts." /
HI "पोषक तिथि। स्वास्थ्य संबंधी दिनचर्या और शुभ कार्यों के लिए उपयुक्त।"
**Jaya (3, 8, 13)**: EN "A tithi for effort and contest. Good for competition and finishing hard tasks." /
HI "प्रयास और प्रतिस्पर्धा की तिथि। मुकाबले और कठिन काम पूरे करने के लिए अच्छी।"
**Purna (5, 10, 15)**: EN "A tithi of completion. Suits wrapping up and setting out on journeys." /
HI "पूर्णता की तिथि। काम समेटने और यात्रा पर निकलने के लिए उपयुक्त।"
**Rikta (4, 9, 14)**: EN "An empty tithi. Keep the day light; avoid big new starts." /
HI "रिक्त तिथि। दिन हल्का रखें, बड़ी नई शुरुआत से बचें।"
**Amavasya**: EN "New moon. A quiet day for rest, reflection and finishing old tasks." /
HI "अमावस्या। विश्राम, चिंतन और पुराने काम निपटाने का शांत दिन।"

## Weekday suits (`vara_<day>`)
- Sunday: EN "Sun's day. Suits authority, health habits and government matters." / HI "सूर्य का दिन। अधिकार, स्वास्थ्य और सरकारी कामों के लिए उपयुक्त।"
- Monday: EN "Moon's day. Suits travel, creativity and caring for others." / HI "चंद्र का दिन। यात्रा, रचनात्मकता और दूसरों की देखभाल के लिए उपयुक्त।"
- Tuesday: EN "Mars's day. Suits courage and property matters; avoid conflict." / HI "मंगल का दिन। साहस और संपत्ति के कामों के लिए उपयुक्त; विवाद से बचें।"
- Wednesday: EN "Mercury's day. Suits trade, learning and communication." / HI "बुध का दिन। व्यापार, पढ़ाई और संवाद के लिए उपयुक्त।"
- Thursday: EN "Jupiter's day. Suits teaching, finance and auspicious starts." / HI "गुरु का दिन। शिक्षण, वित्त और शुभ आरंभ के लिए उपयुक्त।"
- Friday: EN "Venus's day. Suits arts, relationships and comfort." / HI "शुक्र का दिन। कला, रिश्तों और सुख-सुविधा के लिए उपयुक्त।"
- Saturday: EN "Saturn's day. Suits discipline, service and long-term work." / HI "शनि का दिन। अनुशासन, सेवा और दीर्घकालिक काम के लिए उपयुक्त।"

## Cautions
**inauspicious_yoga** (slot `{yoga}`): EN "{yoga} yoga is in force. Double-check schedules and details today." /
HI "आज {yoga} योग है। समय-सारणी और विवरण दो बार जाँच लें।"
**vishti_karana**: EN "Vishti (Bhadra) karana is active for part of the day. Hold new work until it passes." /
HI "आज दिन के एक हिस्से में विष्टि (भद्रा) करण है। नया काम उसके बीतने तक रोकें।"

## Moon-based
**chandra_bala_good**: EN "The Moon is well placed for you today. Steady progress comes easily." /
HI "आज चंद्रमा आपके लिए अनुकूल है। स्थिर प्रगति सहज रहेगी।"
**chandra_bala_poor**: EN "The Moon asks for patience today. Plan clearly and avoid rushing." /
HI "आज चंद्रमा धैर्य माँगता है। साफ़ योजना बनाएँ, जल्दबाज़ी से बचें।"

## Not drafted yet
Gochara by planet and house, Saturn cycles, dasha, Tara Bala, area notes, windows, ingress heads-up.
Draft these only after the reviewer settles the rule tables, so we do not write around rules that change.
