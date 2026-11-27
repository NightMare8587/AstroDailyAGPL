"""Rules that do not depend on the model: crisis messages get a fixed, caring answer, and model replies are
checked against the same tone rules as the content library."""
import re

from ..content.lint import BANNED_EN, BANNED_HI

# Messages about self-harm or suicide never go to the model and never get an astrological answer.
_CRISIS_EN = re.compile(
    r"(suicid|kill(ing|ed)? myself|"
    r"end(ing)? (my (own )?life|it all)|(take|taking|took) my (own )?life|"
    r"(want|wanna|wish|going|plan(ning)?|thinking (of|about)|feel(ing)? like)( to)? (die|dying|be dead)|"
    r"wish i (was|were) dead|(do ?n'?t|do not) want to (live|be alive|be here)|"
    r"self[- ]?harm|(hurt|hurting|cut|cutting|harm|harming) myself|better off (dead|without me)|"
    r"no (reason|point) (to|in) (live|living|go(ing)? on))",
    re.IGNORECASE)
_CRISIS_HI = re.compile(
    r"(आत्म-?हत्या|ख़?ुदकुशी|जान (दे|ले)|मर जाऊँ|मर जाऊं|मर जाना|मरना चाहत|जीना नहीं चाहत|जीने की इच्छा नहीं|"
    r"जिंदगी (खत्म|ख़त्म)|ज़िंदगी (खत्म|ख़त्म)|खुद को (खत्म|नुकसान|चोट))")

CRISIS_REPLY = {
    "en": ("I'm really sorry you're feeling this way, and I'm glad you said it. You don't have to carry this alone. "
           "Please talk to someone right now: in India, Tele-MANAS is free and open 24 hours on 14416 "
           "(or 1-800-891-4416). If you are in immediate danger, call 112. Reaching out to someone you trust "
           "nearby can help too. I'm not able to help with this through astrology, but I'm here to listen."),
    "hi": ("आपने जो बताया, उसके लिए धन्यवाद, और मुझे सचमुच खेद है कि आप ऐसा महसूस कर रहे हैं। आपको यह अकेले नहीं झेलना है। "
           "कृपया अभी किसी से बात करें: भारत में टेली-मानस (Tele-MANAS) निःशुल्क है और 24 घंटे चालू है, नंबर 14416 "
           "(या 1-800-891-4416)। अगर आप तुरंत खतरे में हैं तो 112 पर कॉल करें। पास के किसी भरोसेमंद व्यक्ति से बात करना भी "
           "मदद करता है। इस बात में ज्योतिष मदद नहीं कर सकता, पर मैं सुनने के लिए यहाँ हूँ।"),
}

FALLBACK_REPLY = {
    "en": "I'd rather not answer that in those words. Could you ask it another way? I can help with today's guidance, "
          "good times of day, or what your chart suggests about a theme.",
    "hi": "इस बात का उत्तर इन शब्दों में देना मुझे ठीक नहीं लगता। क्या आप इसे दूसरे तरीके से पूछ सकते हैं? आज के मार्गदर्शन, "
          "दिन के शुभ समय या आपकी कुंडली के किसी विषय पर बात की जा सकती है।",
}


def is_crisis(text: str) -> bool:
    return bool(_CRISIS_EN.search(text) or _CRISIS_HI.search(text))


def breaks_tone_rules(reply: str) -> bool:
    return bool(BANNED_EN.search(reply) or BANNED_HI.search(reply))
