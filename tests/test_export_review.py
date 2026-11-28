from astrodaily.tools import export_review


def test_the_review_document_is_up_to_date_and_covers_every_group():
    text = export_review.build()
    assert export_review.OUT.read_text(encoding="utf-8") == text, "run: python -m astrodaily.tools.export_review"
    for heading in ("What each planet stands for", "How a planet works in each sign", "What each house covers",
                    "What each main period (dasha) is like", "Yogas, doshas and Sade Sati", "Compatibility (Ashtakoota)",
                    "Vashya points", "Yoni animal by birth star", "Nadi by birth star"):
        assert heading in text, heading
    assert text.count("| Sun |") >= 3 and "Mangal dosha" in text and "Gajakesari" in text
