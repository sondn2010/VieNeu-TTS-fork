"""Stage 3 prosody: one test per pause rule P-01…P-14, the countdown ladder and section 4.3."""
import pytest

from vieneu_preprocess import preprocess
from vieneu_preprocess.rules import load_rules

R = load_rules()
P = R.pauses
FILLER_A = "Hắn đứng lặng im bên khung cửa sổ đã vỡ từ lâu."  # 11 words
FILLER_B = "Bên ngoài trời vẫn mưa rả rích suốt cả buổi chiều dài."  # 11 words


def chunks(text, **kw):
    return preprocess(text, **kw).chunks


def pause_after(text, needle):
    return next(c.pause_after_sec for c in chunks(text) if needle in c.text)


def mid(sentence):
    return f"{FILLER_A} {sentence} {FILLER_B}"


def test_p01_short_narration():
    s = "Cô bước chậm rãi qua căn phòng tối om."
    assert pause_after(mid(s), "căn phòng") == P.p01_short_narration


def test_p02_standard_narration():
    s = ("Cô bước chậm rãi qua căn phòng tối om, nơi những chiếc ghế phủ vải trắng "
         "đứng im như những bóng ma.")
    assert pause_after(mid(s), "căn phòng") == P.p02_standard_narration


def test_p03_long_narration():
    s = " ".join(["một"] * 36) + "."
    assert pause_after(mid(s.capitalize()), "một một") == P.p03_long_narration


def test_p04_emphatic_short_at_paragraph_edge():
    assert pause_after(f"Không ai mỉm cười. {FILLER_A}", "Không ai") == P.p04_emphatic_short


def test_short_sentence_mid_paragraph_is_not_p04():
    assert pause_after(mid("Không ai cười."), "Không ai") == P.p01_short_narration


def test_p05_countdown_ladder_and_role():
    out = chunks("Chiếc nón sụp xuống đầu cậu. Một giây trôi qua. Năm giây. Mười giây. Ba mươi giây.")
    cd = [c for c in out if c.role_type == "narration_countdown"]
    assert [c.pause_after_sec for c in cd] == list(R.countdown.ladder)
    assert [c.text for c in cd] == ["Một giây trôi qua...", "Năm giây...", "Mười giây...", "Ba mươi giây..."]
    assert cd[0].speed == R.countdown.speed_ladder[0] and cd[-1].speed == R.countdown.speed_ladder[-1]


def test_p05_two_timed_sentences_still_count():
    out = chunks(f"{FILLER_A} Năm phút. Mười phút. {FILLER_B}")
    assert [c.pause_after_sec for c in out if c.role_type == "narration_countdown"] == [0.6, 0.85]


def test_p06_question_and_exclamation():
    assert pause_after(mid("Liệu hắn có quay lại nơi này nữa không?"), "quay lại") == P.p06_question_exclaim
    assert pause_after(mid("Cánh cửa bỗng bật tung ra giữa đêm khuya!"), "bật tung") == P.p06_question_exclaim


def test_p07_shout_pauses_before_and_after():
    out = chunks(f'{FILLER_A}\n"GRYFFINDOR!"\n{FILLER_B}')
    shout = next(c for c in out if c.role_type == "dialogue_shout")
    assert (shout.pause_before_sec, shout.pause_after_sec) == (P.p07_shout_before, P.p07_shout_after)
    assert shout.text == "Gryffindor!"
    assert shout.speed == R.emotion("shout").speed


def test_roll_call_comma_becomes_soft_and_hard_pause():
    out = [c for c in chunks('"Potter, Harry!"') if c.role_type == "dialogue_shout"]
    assert [(c.text, c.pause_after_sec) for c in out] == [
        ("Potter...", P.roll_call_comma), ("Harry!", P.p07_shout_after)]


def test_p08_dash_pair():
    s = "Ngọn tháp — nơi lão pháp sư từng sống — giờ chỉ còn là đống đổ nát."
    out = chunks(mid(s))
    assert [(c.text, c.pause_after_sec) for c in out[1:3]] == [
        ("Ngọn tháp...", P.p08_dash_pair_open), ("nơi lão pháp sư từng sống...", P.p08_dash_pair_close)]
    assert out[3].text == "giờ chỉ còn là đống đổ nát."


def test_p09_dash_tail():
    out = chunks(mid("Tòa lâu đài hiện ra trên vách đá — một quần thể đồ sộ."))
    assert (out[1].text, out[1].pause_after_sec) == ("Tòa lâu đài hiện ra trên vách đá...", P.p09_dash_tail)
    assert out[2].text == "một quần thể đồ sộ."


def test_p10_long_clause_breath_only_before_connector():
    clause = "Đoàn người lầm lũi bước đi trên con đường mòn phủ đầy tro bụi suốt từ sáng sớm tới tận lúc mặt trời"
    out = chunks(mid(f"{clause}, nhưng không ai dám dừng lại."))
    assert (out[1].text, out[1].pause_after_sec) == (f"{clause},...", P.p10_long_clause_breath)
    no_conn = chunks(mid(f"{clause}, mọi người vẫn không dám dừng lại."))
    assert len(no_conn) == 3


def test_p11_dialogue_intro_colon_and_turn_boundary():
    out = chunks(f'{FILLER_A} Hắn nói: "Chúng ta phải rời khỏi nơi này trước khi trời sáng hẳn."')
    assert next(c for c in out if c.text == "Hắn nói:").pause_after_sec == P.p11_dialogue_narration
    out2 = chunks('"Chúng ta phải rời khỏi nơi này trước khi trời sáng," hắn nói. Rồi hắn quay lưng bước đi thật nhanh.')
    assert out2[0].pause_after_sec == P.p11_dialogue_narration


def test_p12_inner_voice_boundaries():
    text = ("Dracaena ngồi im lặng trên chiếc ghế gỗ cũ kỹ. "
            "Đây đúng là một lựa chọn rất thú vị, chiếc nón thì thầm. Cô không đáp lại lời nào cả.")
    out = chunks(text)
    assert out[0].pause_after_sec == P.p12_inner_voice
    inner = next(c for c in out if c.role_type == "inner_voice")
    assert inner.text == "Đây đúng là một lựa chọn rất thú vị." and inner.pause_after_sec == P.p12_inner_voice
    assert inner.speed == R.emotion("inner").speed


def test_p12_mind_cue_colon_vs_p11_speech_colon():
    from vieneu_preprocess.prosody_annotator import _sentence_end_pause

    assert _sentence_end_pause("Giọng nói vang lên trong tâm trí cô:", 7, False, R) == P.p12_inner_voice
    assert _sentence_end_pause("Rồi chiếc nón hét vang:", 5, False, R) == P.p11_dialogue_narration


def test_p13_paragraph_end_and_p14_scene_break():
    out = chunks(f"{FILLER_A}\n{FILLER_B}\n***\n{FILLER_A}")
    assert out[0].pause_after_sec == P.p13_paragraph
    assert out[1].pause_after_sec == P.p14_scene


def test_embedded_quote_wrap():
    out = chunks('Suốt đêm, câu nói "Chính xác là người mà con phải trở thành" vẫn vương lại trong cô.')
    assert [(c.text, c.pause_after_sec) for c in out[:2]] == [
        ("Suốt đêm, câu nói...", P.embedded_quote_before),
        ('"Chính xác là người mà con phải trở thành"', P.embedded_quote_after)]
    assert all(c.speaker == R.narrator for c in out)


@pytest.mark.parametrize("tag, emotion, text_check", [
    ("cô bật cười", "laugh", lambda t: t.endswith("[cười]")),
    ("hắn thở dài", "sigh", lambda t: t.startswith("[thở dài]")),
    ("bà nghiêm nghị nói", "stern", lambda t: t.startswith("[hắng giọng]")),
])
def test_emotion_tags_and_speed(tag, emotion, text_check):
    out = chunks(f'"Mọi chuyện rồi sẽ ổn cả thôi mà," {tag}.')
    d = out[0]
    assert d.role_type == "dialogue" and text_check(d.text)
    assert d.speed == R.emotion(emotion).speed


def test_fast_emotion_shortens_end_pause():
    out = chunks('"Đi mau lên kẻo không kịp nữa đâu," cô thì thầm rất nhanh. Rồi cô chạy vụt ra khỏi cửa.')
    assert out[0].pause_after_sec == max(R.emotion("fast").end_pause, P.p11_dialogue_narration)
    assert out[0].speed == R.emotion("fast").speed


def test_inner_voice_soft_comma():
    text = "Hắn nghe thấy trong đầu:\nChà, một người nhà Malfoy nữa."
    inner = next(c for c in chunks(text) if c.role_type == "inner_voice")
    assert inner.text.startswith("Chà... một người")


def test_rules_drive_durations(tmp_path):
    custom = tmp_path / "r.yaml"
    custom.write_text("pauses:\n  p13_paragraph: 2.5\ncountdown:\n  ladder: [0.7, 0.9]\n", encoding="utf-8")
    out = chunks(f"{FILLER_A}\n{FILLER_B} Một giây. Hai giây. Ba giây.", rules_path=str(custom))
    assert out[0].pause_after_sec == 2.5
    assert [c.pause_after_sec for c in out if c.role_type == "narration_countdown"] == [0.7, 0.9, 2.5]
