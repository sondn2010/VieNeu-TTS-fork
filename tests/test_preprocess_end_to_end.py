"""End to end on the spec section 5.1 sample, plus exporters, safe execution, rules, perf and CLI."""
import json
import logging
import statistics
import time
from pathlib import Path

import pytest

import vieneu_preprocess
from vieneu_preprocess import LexiconEntry as E, preprocess, preprocess_safely
from vieneu_preprocess.cli import main as cli_main
from vieneu_preprocess.rules import RulesError, load_rules

FIX = Path(__file__).parent / "fixtures" / "preprocess"
CAST = str(FIX / "dracaena_cast_rules.yaml")
HOGWARTS = [E(t, r) for t, r in [
    ("Hogwarts", "Hốc-goát"), ("Hagrid", "Ha-gờ-rít"), ("Malfoy", "Man-phôi"), ("Harry", "Ha-ri"),
    ("Potter", "Pót-tơ"), ("Dracaena", "Đờ-ra-xê-na"), ("Gryffindor", "Gờ-ríp-phin-đo"),
    ("Slytherin", "Sờ-li-thơ-rin"), ("McGonagall", "Mắc-go-na-gôn")]] + [E("Scotland", mode="en")]


@pytest.fixture(scope="module")
def result():
    return preprocess((FIX / "dracaena_input.md").read_text(encoding="utf-8"), HOGWARTS, rules_path=CAST)


def turn_labels(script):
    return [ln.split(":", 1)[0] for ln in script.splitlines() if ln and not ln.startswith("//")]


def test_speaker_turns_match_spec_5_2(result):
    assert turn_labels(result.script) == [
        "Người dẫn", "Người dẫn", "Nón Phân Loại", "Người dẫn", "Nón Phân Loại", "Người dẫn",
        "Nón Phân Loại", "Người dẫn", "Dracaena (Nội tâm)", "McGonagall", "Người dẫn", "Người dẫn",
        "Nón Phân Loại"]
    assert [ln for ln in result.script.splitlines() if ln.startswith("//")] == [
        "// Phân cảnh 1", "// Phân cảnh 2", "// Phân cảnh 3"]


def test_inner_voice_split(result):
    inner = [c for c in result.chunks if c.role_type == "inner_voice"]
    assert {c.speaker for c in inner} == {"Nón Phân Loại", "Dracaena (Nội tâm)"}
    assert any(c.text == "Rất thông minh." for c in inner)
    assert any(c.text == "Chiếc nón thì thầm." and c.speaker == "Narrator" for c in result.chunks)


def test_countdown_pauses(result):
    cd = [c for c in result.chunks if c.role_type == "narration_countdown"]
    assert [c.pause_after_sec for c in cd] == [0.6, 0.85, 1.1, 1.4]
    assert "Một giây trôi qua... [0.6] Năm giây... [0.85] Mười giây... [1.1] Ba mươi giây... [1.4]" in result.script


def test_shout_normalization(result):
    last = result.chunks[-1]
    assert (last.speaker, last.role_type, last.text) == ("Nón Phân Loại", "dialogue_shout", "Gờ-ríp-phin-đo!")
    assert (last.pause_before_sec, last.pause_after_sec) == (0.5, 0.9)
    roll = [c for c in result.chunks if c.speaker == "McGonagall"]
    assert [c.text for c in roll] == ["Pót-tơ...", "Ha-ri!"]
    assert "McGonagall: [0.5] Pót-tơ... [0.25] Ha-ri! [0.9]" not in result.script  # scene pause wins
    assert "McGonagall: Pót-tơ... [0.25] Ha-ri! [0.9]" in result.script


def test_gryffindor_title_case_without_lexicon():
    out = preprocess('"GRYFFINDOR!"')
    assert out.chunks[0].text == "Gryffindor!"
    assert out.to_tagged_text() == "[0.5] Gryffindor! [0.9]"


def test_drop_cap_and_lexicon_names(result):
    assert result.chunks[0].text.startswith("Mặt nước Hồ Đen")
    for name in ("Hốc-goát", "Sờ-li-thơ-rin", "Đờ-ra-xê-na", "Ha-gờ-rít", "<en>Scotland</en>"):
        assert name in result.script
    assert "Dracaena ngồi" not in result.script


def test_json_shape_matches_spec_5_3(result):
    data = result.to_json()
    keys = {"chunk_id", "speaker", "role_type", "text", "speed", "pause_before_sec",
            "pause_after_sec", "voice_preset", "temperature"}
    assert all(set(d) == keys for d in data)
    assert data[0]["chunk_id"] == "ch01_p01_s01"
    assert len({d["chunk_id"] for d in data}) == len(data)
    assert all("[0." not in d["text"] and "[1." not in d["text"] for d in data)


def test_tagged_text_uses_effective_pauses(result):
    tagged = result.to_tagged_text()
    assert "Nón Phân Loại" not in tagged and "Người dẫn" not in tagged
    assert "] [" not in tagged  # one tag per boundary
    assert "Rồi chiếc nón hét vang: [1.0] Gờ-ríp-phin-đo! [0.9]" in tagged


def test_voices_mapping():
    out = preprocess('Trời tối.\n"Đi thôi," hắn nói.', voices={"Người dẫn": "Thiện Minh", "Hắn": "Đoan Trang"})
    assert out.chunks[0].voice_preset == "Thiện Minh"
    assert out.chunks[1].voice_preset == "Đoan Trang"


def test_empty_and_type_validation():
    assert preprocess("   \n").chunks == []
    with pytest.raises(TypeError):
        preprocess(b"bytes")  # type: ignore[arg-type]


def test_safe_execution_falls_back_to_raw_text(monkeypatch, caplog):
    import vieneu_preprocess.pipeline as pipeline

    def boom(*a, **k):
        raise ValueError("anomaly")

    monkeypatch.setattr(pipeline, "run_pipeline", boom)
    raw = "Xin chào [cười] thế giới."
    with caplog.at_level(logging.WARNING):
        outcome = preprocess_safely(raw)
    assert not outcome.ok and outcome.error == "ValueError: anomaly"
    assert outcome.result.to_tagged_text() == raw
    assert "story preprocessor failed" in caplog.text


def test_safe_execution_ok_path_and_bad_rules():
    ok = preprocess_safely("Trời tối.")
    assert ok.ok and ok.result.chunks
    bad = preprocess_safely("Trời tối.", rules_path="does-not-exist.yaml")
    assert not bad.ok and bad.result.to_tagged_text() == "Trời tối."
    with pytest.raises(TypeError):
        preprocess_safely(None)  # type: ignore[arg-type]


def test_rules_validation(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("pauses:\n  p01_short_narration: fast\n", encoding="utf-8")
    with pytest.raises(RulesError):
        load_rules(bad)
    bad.write_text("pauses: [1, 2\n", encoding="utf-8")
    with pytest.raises(RulesError):
        load_rules(bad)
    bad.write_text("pauses:\n  p99_unknown: 1\n", encoding="utf-8")
    with pytest.raises(RulesError):
        load_rules(bad)


def test_performance_5000_word_chapter():
    para = (FIX / "dracaena_input.md").read_text(encoding="utf-8")
    words = len(para.split())
    text = "\n".join([para] * (5000 // words + 1))
    preprocess(text, HOGWARTS)  # warm caches
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        preprocess(text, HOGWARTS)
        times.append((time.perf_counter() - t0) * 1000)
    median = statistics.median(times)
    print(f"5000-word chapter preprocess median: {median:.1f} ms")
    assert median < 100


def test_cli_batch_two_chapters(tmp_path, capsys):
    src = tmp_path / "chapters"
    src.mkdir()
    (src / "ch01.md").write_text((FIX / "dracaena_input.md").read_text(encoding="utf-8"), encoding="utf-8")
    (src / "ch02.html").write_text('<p><span class="dropcap">K</span>hi ông Bilbo về, làng đã ngủ.</p>',
                                   encoding="utf-8")
    dict_file = tmp_path / "hogwarts.json"
    dict_file.write_text(json.dumps({"format": "vieneu-dictionary/1", "name": "HP", "kind": "name",
                                     "entries": [{"term": "Hogwarts", "replacement": "Hốc-goát"}]}),
                         encoding="utf-8")
    out = tmp_path / "out"
    assert cli_main([str(src), "--out", str(out), "--format", "both", "--dict", str(dict_file)]) == 0
    assert sorted(p.name for p in out.iterdir()) == ["ch01.json", "ch01.script.txt", "ch02.json", "ch02.script.txt"]
    assert "Hốc-goát" in (out / "ch01.script.txt").read_text(encoding="utf-8")
    ch2 = json.loads((out / "ch02.json").read_text(encoding="utf-8"))
    assert ch2[0]["text"].startswith("Khi ông Bilbo") and ch2[0]["chunk_id"].startswith("ch02_")


def test_cli_errors(tmp_path):
    assert cli_main([str(tmp_path / "missing.md")]) == 2
    empty = tmp_path / "empty"
    empty.mkdir()
    assert cli_main([str(empty)]) == 2
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    (empty / "a.txt").write_text("Trời tối.", encoding="utf-8")
    with pytest.raises(SystemExit):
        cli_main([str(empty), "--dict", str(bad)])


def test_public_api_exports():
    assert set(vieneu_preprocess.__all__) >= {"preprocess", "render", "preprocess_safely"}
