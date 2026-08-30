from pathlib import Path

from jarvis.config import Settings
from jarvis.core.cognitive_gateway import CognitiveGateway


class FakeVaultBackend:
    principal = "AI_AGENT"

    @staticmethod
    def cognitive_read(_principal, note_id):
        return {
            "results": [
                {
                    "id": note_id,
                    "type": "knowledge",
                    "lifecycle": "ACTIVE",
                    "verification": "verified",
                    "provenance": {
                        "source_type": "official",
                        "source_ref": f"source:{note_id}",
                        "extraction_date": "2026-01-01",
                    },
                    "content": f"evidence {note_id}",
                }
            ]
        }


class FakeBridge:
    available = True
    _backend = FakeVaultBackend()


def test_gateway_acquires_hash_verifiable_evidence_bundle(tmp_path: Path):
    gateway = CognitiveGateway(settings=Settings(vault_path=tmp_path, sync_vault=False), provider=None)
    gateway.vault_bridge = FakeBridge()
    bundle = gateway.acquire_conflict_evidence(
        memory_ids=["m1", "m2"],
        conflict_case_id="CR-test",
        as_of="2026-01-01",
    )
    assert bundle["bundle_id"].startswith("EB-")
    assert bundle["bundle_hash"]
    assert bundle["conflict_case_id"] == "CR-test"
    assert {item["memory_id"] for item in bundle["items"]} == {"m1", "m2"}
    assert all(len(item["content_hash"]) == 64 for item in bundle["items"])
