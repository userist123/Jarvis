from jarvis.memory.context_assembler import ContextAssembler


def test_context_assembler_respects_note_and_character_budget():
    assembler = ContextAssembler(max_chars=500, max_notes=2)
    notes = [
        {"id": "a", "type": "knowledge", "confidence": "high", "verification": "verified", "content": "alpha memory"},
        {"id": "b", "type": "knowledge", "confidence": "medium", "verification": "verified", "content": "beta memory"},
        {"id": "c", "type": "knowledge", "confidence": "high", "verification": "verified", "content": "gamma memory"},
    ]
    result = assembler.assemble(notes)
    assert result.note_ids == ("a", "b")
    assert result.characters <= 500


def test_context_assembler_reports_truncation():
    assembler = ContextAssembler(max_chars=256, max_notes=8)
    result = assembler.assemble([{"id": "a", "content": "x" * 1000}])
    assert result.truncated is True
    assert result.characters <= 256
