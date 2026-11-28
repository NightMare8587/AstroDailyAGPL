# Content for review

Everything below is **draft**: written by a model, not yet checked by a Jyotish reviewer. This file is generated (`python -m astrodaily.tools.export_review`); do not edit it. To change a line, edit the source named under each heading, and to approve a group set its status to `reviewed`. Wording is shown to people only when every part it is built from is reviewed, unless `CHART_MEANINGS_ALLOW_DRAFT` is on (it is on while everything is draft).

## What to check

- Is it true to the tradition, and said as a tendency, never as a fate or a guarantee?
- Is it gentle (nothing frightening about health, loss, marriage or death) and plain (no jargon)?
- Is the Hindi natural, in Devanagari only, in simple everyday words?
- Are the rules and tables in the last section right for the school you follow?

## Status

| Group | Status |
| --- | --- |
| planets | draft |
| sign_style | draft |
| house_area | draft |
| sign_overrides | draft |
| lagna | draft |
| planet_role | draft |
| dasha | draft |

Yogas, doshas and strength words: `draft`.

## What each planet stands for

Source: `chart_meanings.json` → `planets`

| Item | English | Hindi |
| --- | --- | --- |
| Sun | In Vedic astrology the Sun is the soul (atma). It shows your core self: confidence, vitality, purpose, and how you deal with authority and with father figures. | वैदिक ज्योतिष में सूर्य आत्मा है। यह आपका मूल स्वभाव दिखाता है: आत्मविश्वास, ऊर्जा, उद्देश्य, और अधिकारियों व पिता समान लोगों के साथ आपका व्यवहार। |
| Moon | The Moon is the mind. It shows how you feel and react, what makes you feel safe, and your bond with your mother. Its sign is your Moon sign (rashi), the one used for daily predictions and for the dasha periods. | चंद्रमा मन है। यह दिखाता है कि आप कैसा महसूस करते हैं और कैसे प्रतिक्रिया देते हैं, किस बात से सुरक्षित लगता है, और माँ से आपका जुड़ाव। इसकी राशि आपकी चंद्र राशि है, जिससे दैनिक फल और दशा देखी जाती है। |
| Mars | Mars is energy and courage. It shows how you take action, handle conflict and push through effort, and it relates to siblings and property. | मंगल ऊर्जा और साहस है। यह दिखाता है कि आप कैसे कदम उठाते हैं, टकराव को कैसे संभालते हैं और मेहनत कैसे करते हैं; यह भाई-बहन और संपत्ति से भी जुड़ा है। |
| Mercury | Mercury is the intellect. It shows how you think, speak, learn and trade, and how quickly you pick things up. | बुध बुद्धि है। यह दिखाता है कि आप कैसे सोचते, बोलते, सीखते और लेन-देन करते हैं, और बातें कितनी जल्दी समझते हैं। |
| Jupiter | Jupiter is wisdom and growth. It shows where you find guidance, luck and generosity, and it relates to teachers, learning and family values. | गुरु ज्ञान और विकास है। यह दिखाता है कि आपको मार्गदर्शन, सौभाग्य और उदारता कहाँ मिलती है; यह गुरु, शिक्षा और पारिवारिक मूल्यों से जुड़ा है। |
| Venus | Venus is love and comfort. It shows how you relate to others, what you find beautiful, and your approach to pleasure, art and money. | शुक्र प्रेम और सुख है। यह दिखाता है कि आप दूसरों से कैसे जुड़ते हैं, आपको क्या सुंदर लगता है, और सुख, कला व धन के प्रति आपका नज़रिया। |
| Saturn | Saturn is discipline and time. It shows where you work hard and slowly, learn patience and build things that last. | शनि अनुशासन और समय है। यह दिखाता है कि आप कहाँ धीरे-धीरे और कड़ी मेहनत करते हैं, धैर्य सीखते हैं और टिकाऊ चीज़ें बनाते हैं। |
| Rahu | Rahu is ambition and the pull of the new. It shows where you reach beyond the familiar and where you may feel restless or hungry for more. It is a shadow point (a lunar node), not a physical planet. | राहु महत्वाकांक्षा और नएपन का खिंचाव है। यह दिखाता है कि आप कहाँ जाने-पहचाने से आगे बढ़ना चाहते हैं और कहाँ बेचैनी या और पाने की चाह रहती है। यह एक छाया बिंदु (चंद्र पात) है, भौतिक ग्रह नहीं। |
| Ketu | Ketu is detachment and inner insight. It shows where you need less, let go easily or turn inward. It is a shadow point (a lunar node), not a physical planet. | केतु वैराग्य और भीतरी समझ है। यह दिखाता है कि आपको कहाँ कम की ज़रूरत है, कहाँ छोड़ना आसान है या मन भीतर मुड़ता है। यह एक छाया बिंदु (चंद्र पात) है, भौतिक ग्रह नहीं। |

## Each planet's themes in a few words

Source: `planet_role` (used in the planet-in-sign, planet-in-house and sub-period lines)

| Item | English | Hindi |
| --- | --- | --- |
| Sun | self, confidence and purpose | स्वयं, आत्मविश्वास और उद्देश्य |
| Moon | mind, feelings and comfort | मन, भावनाओं और सुकून |
| Mars | energy, courage and drive | ऊर्जा, साहस और उत्साह |
| Mercury | thinking, speech and learning | सोच, वाणी और सीखने |
| Jupiter | wisdom, growth and guidance | ज्ञान, विकास और मार्गदर्शन |
| Venus | love, comfort and beauty | प्रेम, सुख और सुंदरता |
| Saturn | discipline, patience and duty | अनुशासन, धैर्य और कर्तव्य |
| Rahu | ambition, appetite and the new | महत्वाकांक्षा, चाह और नएपन |
| Ketu | detachment, insight and letting go | वैराग्य, अंतर्दृष्टि और छोड़ने |

## How a planet works in each sign

Source: `sign_style`; the line reads: In {sign}, the themes of {role} work {style}.

| Item | English | Hindi |
| --- | --- | --- |
| Aries | boldly and directly, quick to start | साहस और सीधेपन से, शुरुआत करने में तेज़ |
| Taurus | steadily and practically, valuing comfort and security | स्थिरता और व्यावहारिकता से, सुख और सुरक्षा को महत्व देते हुए |
| Gemini | curiously and quickly, through talking, learning and variety | जिज्ञासा और तेज़ी से, बातचीत, सीखने और विविधता के ज़रिए |
| Cancer | with care and feeling, tied to home and family | देखभाल और भावना से, घर और परिवार से जुड़कर |
| Leo | warmly and proudly, wanting to be seen and to lead | गर्मजोशी और स्वाभिमान से, आगे आने और नेतृत्व करने की चाह के साथ |
| Virgo | carefully and analytically, improving things through detail | सावधानी और विश्लेषण से, बारीकी के ज़रिए चीज़ें बेहतर करते हुए |
| Libra | fairly and sociably, looking for balance and partnership | न्याय और मिलनसारी से, संतुलन और साझेदारी की तलाश में |
| Scorpio | intensely and privately, looking beneath the surface | तीव्रता और गोपनीयता से, सतह के नीचे झाँकते हुए |
| Sagittarius | hopefully and openly, drawn to learning, travel and meaning | आशा और खुलेपन से, सीखने, यात्रा और अर्थ की ओर खिंचते हुए |
| Capricorn | with discipline and patience, aiming at long goals | अनुशासन और धैर्य से, लंबे लक्ष्यों की ओर |
| Aquarius | independently and idealistically, thinking of groups and the future | स्वतंत्रता और आदर्शवाद से, समूह और भविष्य के बारे में सोचते हुए |
| Pisces | gently and intuitively, drawn to compassion and the inner life | कोमलता और सहज-बोध से, करुणा और भीतरी जीवन की ओर खिंचते हुए |

## What each house covers

Source: `house_area`; the line reads: In house {n}, the themes of {role} work through {area}.

| Item | English | Hindi |
| --- | --- | --- |
| House 1 | your body, personality and first impression | आपके शरीर, व्यक्तित्व और पहले प्रभाव |
| House 2 | money, family and speech | धन, परिवार और वाणी |
| House 3 | courage, effort, siblings and communication | साहस, प्रयास, भाई-बहन और संवाद |
| House 4 | home, mother, property and inner peace | घर, माँ, संपत्ति और मन की शांति |
| House 5 | creativity, children, learning and romance | रचनात्मकता, संतान, विद्या और प्रेम |
| House 6 | daily work, health habits, service and obstacles | रोज़ के काम, स्वास्थ्य की आदतें, सेवा और बाधाएँ |
| House 7 | partnerships, marriage and close dealings with others | साझेदारी, विवाह और दूसरों से निकट व्यवहार |
| House 8 | change, shared resources, research and the hidden side of things | बदलाव, साझा संसाधन, शोध और चीज़ों का छिपा पक्ष |
| House 9 | luck, beliefs, teachers, higher learning and long journeys | भाग्य, आस्था, गुरु, उच्च शिक्षा और लंबी यात्राएँ |
| House 10 | career, status and your public role | करियर, प्रतिष्ठा और आपकी सार्वजनिक भूमिका |
| House 11 | gains, friends, networks and fulfilment of wishes | लाभ, मित्र, संपर्क और इच्छाओं की पूर्ति |
| House 12 | rest, solitude, spending, foreign places and letting go | विश्राम, एकांत, खर्च, विदेश और छोड़ना |

## Hand-written lines for a body in a sign

Source: `sign_overrides` (these win over the sign style)

### Sun

| Item | English | Hindi |
| --- | --- | --- |
| Aries | Bold, direct and quick to start. You lead by acting first. Impatience is the thing to watch. | साहसी, सीधे और शुरुआत करने में तेज। आप पहले कदम उठाकर नेतृत्व करते हैं। जल्दबाज़ी पर ध्यान रखें। |
| Taurus | Steady, practical and loyal. You build slowly and value comfort and security. | स्थिर, व्यावहारिक और वफ़ादार। आप धीरे-धीरे निर्माण करते हैं और सुख व सुरक्षा को महत्व देते हैं। |
| Gemini | Curious, quick and talkative. You learn by exchanging ideas and like variety. | जिज्ञासु, तेज़ और बातूनी। आप विचारों के आदान-प्रदान से सीखते हैं और विविधता पसंद करते हैं। |
| Cancer | Caring and protective. Your sense of self is tied to family, home and feelings. | देखभाल करने वाले और रक्षक। आपकी पहचान परिवार, घर और भावनाओं से जुड़ी होती है। |
| Leo | Warm, proud and generous. You want to be seen and you lead with heart. | गर्मजोशी वाले, स्वाभिमानी और उदार। आप चाहते हैं कि आपको देखा जाए और आप दिल से नेतृत्व करते हैं। |
| Virgo | Careful, analytical and helpful. You improve things through detail and service. | सावधान, विश्लेषण करने वाले और मददगार। आप बारीकी और सेवा से चीज़ें बेहतर बनाते हैं। |
| Libra | Fair-minded and sociable. You look for balance and do well in partnerships. | न्यायप्रिय और मिलनसार। आप संतुलन चाहते हैं और साझेदारी में अच्छा करते हैं। |
| Scorpio | Intense, private and determined. You look beneath the surface of things. | तीव्र, अंतर्मुखी और दृढ़। आप चीज़ों की गहराई तक देखते हैं। |
| Sagittarius | Hopeful, honest and drawn to learning, travel and meaning. | आशावादी, ईमानदार और सीखने, यात्रा व अर्थ की खोज की ओर आकर्षित। |
| Capricorn | Disciplined and ambitious. You work patiently towards long goals. | अनुशासित और महत्वाकांक्षी। आप लंबे लक्ष्यों की ओर धैर्य से काम करते हैं। |
| Aquarius | Independent and idealistic. You think about groups, ideas and the future. | स्वतंत्र और आदर्शवादी। आप समूह, विचार और भविष्य के बारे में सोचते हैं। |
| Pisces | Gentle, imaginative and intuitive. You are drawn to compassion and the inner life. | कोमल, कल्पनाशील और सहज-बोध वाले। आप करुणा और भीतरी जीवन की ओर खिंचते हैं। |

### Moon

| Item | English | Hindi |
| --- | --- | --- |
| Aries | You feel quickly and want to act on it. Doing something is how you settle. | आप जल्दी महसूस करते हैं और उस पर कुछ करना चाहते हैं। कुछ करने से ही आप शांत होते हैं। |
| Taurus | Calm and comfort-loving. You need routine and are slow to change your mind. | शांत और आराम पसंद। आपको दिनचर्या चाहिए और आप राय बदलने में धीमे हैं। |
| Gemini | A restless, lively mind. Talking, reading and moving around settle you. | चंचल और सक्रिय मन। बात करना, पढ़ना और घूमना आपको शांत करता है। |
| Cancer | Deeply sensitive and nurturing. You need home and a sense of belonging. | गहरे संवेदनशील और पालन करने वाले। आपको घर और अपनेपन का एहसास चाहिए। |
| Leo | Big-hearted and expressive. You need appreciation and warmth around you. | बड़े दिल वाले और अभिव्यक्त। आपको सराहना और अपनापन चाहिए। |
| Virgo | You think things through and can worry. Order and useful work calm you. | आप हर बात पर सोचते हैं और चिंता कर सकते हैं। व्यवस्था और उपयोगी काम आपको शांत करते हैं। |
| Libra | You need harmony and dislike conflict. Company and fairness steady you. | आपको सामंजस्य चाहिए और टकराव पसंद नहीं। साथ और निष्पक्षता आपको स्थिर रखते हैं। |
| Scorpio | Deep, guarded feelings with a strong memory and strong loyalty. | गहरी और छिपी हुई भावनाएँ, मज़बूत याददाश्त और गहरी निष्ठा। |
| Sagittarius | Hopeful and free-spirited. You need space and a purpose to look towards. | आशावादी और स्वतंत्र मन। आपको खुली जगह और आगे देखने के लिए उद्देश्य चाहिए। |
| Capricorn | Reserved and controlled with feelings. You stay steady under pressure. | भावनाओं में संयमित और कम बोलने वाले। दबाव में भी स्थिर रहते हैं। |
| Aquarius | Thoughtful and a little detached. You need friends and your own freedom. | विचारशील और थोड़े निर्लिप्त। आपको मित्र और अपनी आज़ादी चाहिए। |
| Pisces | Empathic and dreamy. You need quiet and time alone to recover. | सहानुभूतिपूर्ण और स्वप्निल। उबरने के लिए आपको शांति और अकेला समय चाहिए। |

### Lagna

| Item | English | Hindi |
| --- | --- | --- |
| Aries | You come across as energetic and direct, quick to begin and slow to wait. | आप ऊर्जावान और सीधे दिखते हैं, शुरू करने में तेज़ और इंतज़ार में धीमे। |
| Taurus | You come across as calm, steady and pleasant, with a liking for comfort. | आप शांत, स्थिर और सुखद लगते हैं, और आराम पसंद करते हैं। |
| Gemini | You come across as lively, curious and talkative, often looking young. | आप चंचल, जिज्ञासु और बातूनी लगते हैं, और अक्सर युवा दिखते हैं। |
| Cancer | You come across as gentle and sensitive; your mood tends to show on your face. | आप कोमल और संवेदनशील लगते हैं; आपका मूड अक्सर चेहरे पर दिखता है। |
| Leo | You come across as confident and dignified, a natural presence in a room. | आप आत्मविश्वासी और गरिमामय लगते हैं, किसी भी सभा में आपकी उपस्थिति दिखती है। |
| Virgo | You come across as modest, neat and observant, careful in how you act. | आप विनम्र, सुव्यवस्थित और पैनी नज़र वाले लगते हैं, और सोच-समझकर चलते हैं। |
| Libra | You come across as charming, courteous and tactful, with an eye for beauty. | आप आकर्षक, शिष्ट और व्यवहारकुशल लगते हैं, और सुंदरता की परख रखते हैं। |
| Scorpio | You come across as intense, magnetic and reserved, with strong willpower. | आप तीव्र, चुंबकीय और संयमित लगते हैं, और इच्छाशक्ति मज़बूत है। |
| Sagittarius | You come across as open, cheerful and honest, with a love of freedom. | आप खुले, प्रसन्न और ईमानदार लगते हैं, और आज़ादी पसंद करते हैं। |
| Capricorn | You come across as serious, mature and responsible, a patient builder. | आप गंभीर, परिपक्व और ज़िम्मेदार लगते हैं, एक धैर्यवान निर्माता। |
| Aquarius | You come across as friendly, thoughtful and a little unconventional. | आप मिलनसार, विचारशील और थोड़े अलग तरह के लगते हैं। |
| Pisces | You come across as soft, kind and dreamy, adaptable and private. | आप कोमल, दयालु और स्वप्निल लगते हैं, लचीले और निजी स्वभाव के। |

## The Lagna

Source: `lagna`

- English: The Lagna (ascendant) is the sign that was rising on the eastern horizon at the moment you were born. It shows your body, your first impression and your approach to life, and it is the starting point of the twelve houses.
- Hindi: लग्न वह राशि है जो आपके जन्म के क्षण पूर्वी क्षितिज पर उदय हो रही थी। यह आपका शरीर, पहला प्रभाव और जीवन के प्रति दृष्टिकोण दिखाता है, और बारह भावों की शुरुआत यहीं से होती है।

## What each main period (dasha) is like

Source: `dasha`; a sub-period reads: In this stretch the themes of {main} ({main_role}) are coloured by {sub} ({sub_role}).

| Item | English | Hindi |
| --- | --- | --- |
| Sun | The Sun period puts self-expression, confidence and responsibility in front. It is a time to stand in your own authority, build your standing and look at your relationship with fathers and leaders. | सूर्य की दशा में आत्म-अभिव्यक्ति, आत्मविश्वास और ज़िम्मेदारी आगे आती है। यह अपने अधिकार में खड़े होने, अपनी साख बनाने और पिता व मार्गदर्शकों से अपने संबंध को देखने का समय है। |
| Moon | The Moon period turns attention to feelings, home, family and rest. Moods may feel more tidal, so routine, nourishing company and care of the mind help most. | चंद्र की दशा में ध्यान भावनाओं, घर, परिवार और विश्राम पर जाता है। मन का उतार-चढ़ाव ज़्यादा महसूस हो सकता है, इसलिए दिनचर्या, अपनों का साथ और मन की देखभाल सबसे ज़्यादा काम आती है। |
| Mars | The Mars period brings energy, drive and the urge to act. It favours courage, fitness, building and healthy competition; patience and well-aimed effort keep the heat useful. | मंगल की दशा ऊर्जा, जोश और कुछ कर गुज़रने की चाह लाती है। यह साहस, सेहत, निर्माण और स्वस्थ प्रतिस्पर्धा के लिए अच्छी है; धैर्य और सही दिशा का प्रयास इस ताप को काम का बनाए रखता है। |
| Rahu | The Rahu period is a time of ambition and the new. Interests may stretch beyond the familiar, towards new places, technology or ideas, so grounding habits help you enjoy the pull without chasing every spark. | राहु की दशा महत्वाकांक्षा और नएपन का समय है। रुचियाँ जाने-पहचाने से आगे, नई जगहों, तकनीक या विचारों की ओर बढ़ सकती हैं; टिकाऊ आदतें इस खिंचाव का आनंद लेने में मदद करती हैं। |
| Jupiter | The Jupiter period favours learning, guidance, growth and goodwill. It is a good stretch for study, teaching, faith, family growth and widening your circle. | गुरु की दशा सीखने, मार्गदर्शन, विकास और शुभेच्छा के लिए अनुकूल है। यह पढ़ाई, सिखाने, आस्था, परिवार के विस्तार और अपना दायरा बढ़ाने का अच्छा समय है। |
| Saturn | The Saturn period rewards patience, discipline and steady work. Things may move slowly, but effort put in now tends to build lasting foundations and maturity. | शनि की दशा धैर्य, अनुशासन और लगातार मेहनत का फल देती है। चीज़ें धीमी चल सकती हैं, पर अभी लगाया गया प्रयास टिकाऊ नींव और परिपक्वता बनाता है। |
| Mercury | The Mercury period lights up thinking, learning, trade and communication. It suits study, writing, skills, business and staying curious. | बुध की दशा सोच, सीखने, व्यापार और संवाद को रोशन करती है। यह पढ़ाई, लेखन, हुनर, कारोबार और जिज्ञासु बने रहने के लिए ठीक है। |
| Ketu | The Ketu period turns inward: detachment, reflection and letting go of what no longer fits. It can bring quiet, spiritual interest and a wish to simplify. | केतु की दशा भीतर की ओर मोड़ती है: विरक्ति, चिंतन और जो अब नहीं जँचता उसे छोड़ना। इसमें शांति, आध्यात्मिक रुचि और जीवन को सरल करने की चाह आ सकती है। |
| Venus | The Venus period highlights love, beauty, comfort and the arts. Relationships, creativity and the pleasures of life come forward; moderation keeps them sweet. | शुक्र की दशा प्रेम, सौंदर्य, सुख-सुविधा और कलाओं को उभारती है। रिश्ते, रचनात्मकता और जीवन के सुख आगे आते हैं; संयम इन्हें मधुर बनाए रखता है। |

## Yogas, doshas and Sade Sati

Source: `astrodaily/content/yoga_text.py`. Rules in `astrodaily/calc/yogas.py`: Mangal dosha = Mars in house 1, 2, 4, 7, 8 or 12 from the Lagna; Kaal Sarp = all seven planets on one side of Rahu and Ketu; Gajakesari = Jupiter in house 1, 4, 7 or 10 from the Moon; Budhaditya = Sun and Mercury in one sign; Chandra-Mangal = Moon and Mars in one sign; the five Mahapurusha yogas = Mars, Mercury, Jupiter, Venus or Saturn in its own or high sign in house 1, 4, 7 or 10; Sade Sati = Saturn now in the sign before, on, or after the Moon sign.

| Item | English | Hindi |
| --- | --- | --- |
| Mangal dosha / मंगल दोष | Mars stands in a house that tradition watches closely for partnerships. It is read as strong, direct energy in close relationships, so patience, honest talk and shared goals help. How much it matters depends on the rest of the chart, and many people with it have happy partnerships. | मंगल ऐसे भाव में है जिसे परंपरा में साझेदारी के लिए ध्यान से देखा जाता है। इसे नज़दीकी रिश्तों में तेज़, सीधी ऊर्जा की तरह पढ़ा जाता है, इसलिए धैर्य, खुली बातचीत और साझा लक्ष्य मदद करते हैं। इसका असर बाकी कुंडली पर निर्भर करता है, और इसके साथ भी बहुत से लोगों के रिश्ते सुखी होते हैं। |
| Kaal Sarp yoga / काल सर्प योग | All seven planets sit on one side of the Rahu and Ketu axis. Tradition reads this as a life with a strong single thread: periods of intense focus and learning, with results that come in waves. Steady routines and patience suit it. | सातों ग्रह राहु-केतु की धुरी के एक ही ओर हैं। परंपरा इसे एक मज़बूत सूत्र वाले जीवन की तरह पढ़ती है: गहन एकाग्रता और सीख के दौर, और नतीजे लहरों में आते हैं। नियमित दिनचर्या और धैर्य इसके साथ अच्छे बैठते हैं। |
| Gajakesari yoga / गजकेसरी योग | Jupiter stands in a pillar house from the Moon. It is read as goodwill, good counsel and respect that grows over time, with wisdom helping when choices get hard. | गुरु चंद्र से केंद्र भाव में है। इसे शुभेच्छा, अच्छी सलाह और समय के साथ बढ़ने वाले सम्मान की तरह पढ़ा जाता है; कठिन चुनावों में विवेक साथ देता है। |
| Budhaditya yoga / बुधादित्य योग | The Sun and Mercury share a sign. It is read as a sharp, clear mind and a gift for expression and reasoning. | सूर्य और बुध एक ही राशि में हैं। इसे तेज़, साफ़ दिमाग और अभिव्यक्ति व तर्क की क्षमता की तरह पढ़ा जाता है। |
| Chandra-Mangal yoga / चंद्र-मंगल योग | The Moon and Mars share a sign. It is read as drive joined to feeling, with a knack for earning and for acting on what you care about. | चंद्र और मंगल एक ही राशि में हैं। इसे भावना से जुड़े जोश की तरह पढ़ा जाता है, जिसमें कमाने और अपनी पसंद के काम पर अमल करने की सहजता होती है। |
| Ruchaka yoga / रुचक योग | Mars is strong in its own or its high sign and stands in a pillar house. It is read as courage, stamina and a leader's drive. | मंगल अपनी या उच्च राशि में मज़बूत है और केंद्र भाव में है। इसे साहस, सहनशक्ति और नेतृत्व के जोश की तरह पढ़ा जाता है। |
| Bhadra yoga / भद्र योग | Mercury is strong in its own or its high sign and stands in a pillar house. It is read as quick intelligence, skill with words and good business sense. | बुध अपनी या उच्च राशि में मज़बूत है और केंद्र भाव में है। इसे तेज़ बुद्धि, शब्दों की कुशलता और अच्छी व्यावसायिक समझ की तरह पढ़ा जाता है। |
| Hamsa yoga / हंस योग | Jupiter is strong in its own or its high sign and stands in a pillar house. It is read as wisdom, kindness and a calm, respected presence. | गुरु अपनी या उच्च राशि में मज़बूत है और केंद्र भाव में है। इसे विवेक, दयालुता और शांत, सम्मानित व्यक्तित्व की तरह पढ़ा जाता है। |
| Malavya yoga / मालव्य योग | Venus is strong in its own or its high sign and stands in a pillar house. It is read as charm, a love of beauty and comfort, and warm relationships. | शुक्र अपनी या उच्च राशि में मज़बूत है और केंद्र भाव में है। इसे आकर्षण, सौंदर्य व सुख-सुविधा के प्रेम और स्नेहपूर्ण रिश्तों की तरह पढ़ा जाता है। |
| Shasha yoga / शश योग | Saturn is strong in its own or its high sign and stands in a pillar house. It is read as discipline, endurance and authority earned through steady work. | शनि अपनी या उच्च राशि में मज़बूत है और केंद्र भाव में है। इसे अनुशासन, सहनशक्ति और लगातार मेहनत से कमाए अधिकार की तरह पढ़ा जाता है। |
| Sade Sati / साढ़े साती | Saturn is now moving through the sign before, over, or after your Moon sign. Tradition calls this a long stretch of slow, serious lessons about responsibility and patience. It is a season of steady work and simplifying, and many people find it builds strength. | शनि अभी आपकी चंद्र राशि से एक राशि पहले, उसी राशि में या उसके बाद की राशि में चल रहा है। परंपरा इसे ज़िम्मेदारी और धैर्य के धीमे, गंभीर पाठों का लंबा दौर कहती है। यह लगातार मेहनत और जीवन को सरल करने का मौसम है, और बहुत से लोगों को यह मज़बूत बनाता है। |

### Planet strength words

| Item | English | Hindi |
| --- | --- | --- |
| strong | Strong | मज़बूत |
| steady | Steady | स्थिर |
| tender | Tender | नाज़ुक |

The strength guide gives points for the sign (exalted +3, own +2, a friend's +1, an enemy's −1, debilitated −3; the nodes have none), for the house (houses 1, 4, 5, 7, 9, 10 +1; houses 6, 8, 12 −1) and −1 when a planet is within its combustion distance of the Sun. 3 or more is *strong*, 0 to 2 *steady*, below 0 *tender*. Planets look at the 7th house from where they stand; Mars also the 4th and 8th, Jupiter the 5th and 9th, Saturn the 3rd and 10th, Rahu and Ketu the 5th and 9th.

## Compatibility (Ashtakoota)

Source: `astrodaily/calc/matching.py` and `docs/compatibility.md`. Points: Varna 1, Vashya 2, Tara 3, Yoni 4, Graha Maitri 5, Gana 6, Bhakoot 7, Nadi 8. The first person is the first column of the tables. Where books differ (Varna of the earth and air signs, the Vashya table and the Sagittarius and Capricorn halves, Tara, Gana for the first and second person) please say which you follow.

### Varna by Moon sign

| Sign | Varna |  |
| --- | --- | --- |
| Aries | Kshatriya |  |
| Taurus | Vaishya |  |
| Gemini | Shudra |  |
| Cancer | Brahmin |  |
| Leo | Kshatriya |  |
| Virgo | Vaishya |  |
| Libra | Shudra |  |
| Scorpio | Brahmin |  |
| Sagittarius | Kshatriya |  |
| Capricorn | Vaishya |  |
| Aquarius | Shudra |  |
| Pisces | Brahmin |  |

### Gana by birth star

| Star number | Gana |  |
| --- | --- | --- |
| 1 | Deva |  |
| 2 | Manushya |  |
| 3 | Rakshasa |  |
| 4 | Manushya |  |
| 5 | Deva |  |
| 6 | Manushya |  |
| 7 | Deva |  |
| 8 | Deva |  |
| 9 | Rakshasa |  |
| 10 | Rakshasa |  |
| 11 | Manushya |  |
| 12 | Manushya |  |
| 13 | Deva |  |
| 14 | Rakshasa |  |
| 15 | Deva |  |
| 16 | Rakshasa |  |
| 17 | Deva |  |
| 18 | Rakshasa |  |
| 19 | Rakshasa |  |
| 20 | Manushya |  |
| 21 | Manushya |  |
| 22 | Deva |  |
| 23 | Rakshasa |  |
| 24 | Rakshasa |  |
| 25 | Manushya |  |
| 26 | Manushya |  |
| 27 | Deva |  |

### Gana points (first person, second person)

| Pair | Points |  |
| --- | --- | --- |
| Deva / Deva | 6 |  |
| Deva / Manushya | 5 |  |
| Deva / Rakshasa | 1 |  |
| Manushya / Deva | 6 |  |
| Manushya / Manushya | 6 |  |
| Manushya / Rakshasa | 0 |  |
| Rakshasa / Deva | 0 |  |
| Rakshasa / Manushya | 0 |  |
| Rakshasa / Rakshasa | 6 |  |

### Vashya points (first person's group down, second person's across)

| | Chatushpada | Manava | Jalachara | Vanachara | Keeta |
| --- | --- | --- | --- | --- | --- |
| Chatushpada | 2 | 1 | 1 | 0 | 1 |
| Manava | 1 | 2 | 1.5 | 0 | 1 |
| Jalachara | 1 | 1.5 | 2 | 0 | 1 |
| Vanachara | 1.5 | 0 | 1 | 2 | 0 |
| Keeta | 1 | 1 | 1 | 0 | 2 |

### Yoni animal by birth star

| Star number | Animal |  |
| --- | --- | --- |
| 1 | Horse |  |
| 2 | Elephant |  |
| 3 | Sheep |  |
| 4 | Serpent |  |
| 5 | Serpent |  |
| 6 | Dog |  |
| 7 | Cat |  |
| 8 | Sheep |  |
| 9 | Cat |  |
| 10 | Rat |  |
| 11 | Rat |  |
| 12 | Cow |  |
| 13 | Buffalo |  |
| 14 | Tiger |  |
| 15 | Buffalo |  |
| 16 | Tiger |  |
| 17 | Deer |  |
| 18 | Deer |  |
| 19 | Dog |  |
| 20 | Monkey |  |
| 21 | Mongoose |  |
| 22 | Monkey |  |
| 23 | Lion |  |
| 24 | Horse |  |
| 25 | Lion |  |
| 26 | Cow |  |
| 27 | Elephant |  |

### Nadi by birth star

| Star number | Nadi |  |
| --- | --- | --- |
| 1 | Aadi |  |
| 2 | Madhya |  |
| 3 | Antya |  |
| 4 | Antya |  |
| 5 | Madhya |  |
| 6 | Aadi |  |
| 7 | Aadi |  |
| 8 | Madhya |  |
| 9 | Antya |  |
| 10 | Antya |  |
| 11 | Madhya |  |
| 12 | Aadi |  |
| 13 | Aadi |  |
| 14 | Madhya |  |
| 15 | Antya |  |
| 16 | Antya |  |
| 17 | Madhya |  |
| 18 | Aadi |  |
| 19 | Aadi |  |
| 20 | Madhya |  |
| 21 | Antya |  |
| 22 | Antya |  |
| 23 | Madhya |  |
| 24 | Aadi |  |
| 25 | Aadi |  |
| 26 | Madhya |  |
| 27 | Antya |  |

## Daily horoscope, love reading, planet cards and match summary

These are written by the model from computed facts, so there is no fixed wording to review. The instructions the model follows are in `astrodaily/chat/prompt.py` (`DAILY_SYSTEM`, `LOVE_SYSTEM`, `PLANET_CARDS_SYSTEM`, `MATCH_SYSTEM`): please read them, and the planet chosen for each life area (career Saturn, money Jupiter, relationships Venus, health and energy Mars, mind Mercury).
