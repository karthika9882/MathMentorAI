def choose_support(profile: dict, is_correct: bool) -> dict:
    correct = profile["correct_streak"]
    wrong = profile["wrong_streak"]
    level = profile["support_level"]
    if is_correct:
        correct += 1
        wrong = 0
        if correct >= 3:
            level = "independent"
        elif correct >= 2 and level == "guided":
            level = "balanced"
    else:
        wrong += 1
        correct = 0
        if wrong >= 2:
            level = "guided"
        elif level == "independent":
            level = "balanced"
    messages = {
      "en": {"guided":"Let's slow down and work through each step together.",
             "balanced":"Good progress. Try the next step yourself, then check it.",
             "independent":"Try a similar problem independently."},
      "ta": {"guided":"நிதானமாக ஒவ்வொரு படியாகவும் சேர்ந்து செய்வோம்.",
             "balanced":"நல்ல முன்னேற்றம். அடுத்த படியை நீங்களே முயற்சி செய்யுங்கள்.",
             "independent":"அடுத்த கணக்கைத் தனியாக முயற்சி செய்யுங்கள்."}}
    return {"support_level":level,"correct_streak":correct,"wrong_streak":wrong,
            "message_en":messages["en"][level],"message_ta":messages["ta"][level]}
