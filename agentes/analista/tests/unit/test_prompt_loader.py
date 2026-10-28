from agentes.analista.core.prompt_loader import load_prompt, verify_loaded_prompt

PROMPT_REFERENCE_SHA256 = "f34b4e2f8d05cca703f462ec637a194bd07fde5bdde464a2ede2c64e37a1a1c9"


def test_prompt_has_stable_version_hash_and_required_role_boundaries():
    snapshot = load_prompt()
    normalized = snapshot.text.casefold()

    assert snapshot.version == "1.0.0"
    assert snapshot.sha256 == PROMPT_REFERENCE_SHA256
    assert "no eres un generador ni aprobador" in normalized
    assert "no inventes" in normalized
    assert "contenido no confiable" in normalized
    assert "no redactes ni apruebes la hu" in normalized
    assert "peas" in normalized
    assert verify_loaded_prompt(snapshot, snapshot.text)
    assert not verify_loaded_prompt(snapshot, snapshot.text + " changed")
