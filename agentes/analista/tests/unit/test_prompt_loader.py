from agentes.analista.core.prompt_loader import load_prompt, verify_loaded_prompt

PROMPT_REFERENCE_SHA256 = "c041335e630996326cc11a29fb4fbfaec95818b9a6b79fc0f58d2e5e07fa1870"


def test_prompt_has_stable_version_hash_and_required_role_boundaries():
    snapshot = load_prompt()
    normalized = snapshot.text.casefold()

    assert snapshot.version == "1.6.0"
    assert snapshot.sha256 == PROMPT_REFERENCE_SHA256
    assert "no eres un generador ni aprobador" in normalized
    assert "no inventes" in normalized
    assert "contenido no confiable" in normalized
    assert "no redactes ni apruebes la hu" in normalized
    assert "peas" in normalized
    assert "cita su id" in normalized
    assert "nunca pongas el id dentro del texto de la pregunta" in normalized
    assert "sin conocimientos técnicos" in normalized
    assert "pólizas, personas y seguridad" in normalized
    assert "historias de usuario" in normalized and "storycraft" not in normalized
    assert verify_loaded_prompt(snapshot, snapshot.text)
    assert not verify_loaded_prompt(snapshot, snapshot.text + " changed")
