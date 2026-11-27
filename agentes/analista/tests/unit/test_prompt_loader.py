from agentes.analista.core.prompt_loader import load_prompt, verify_loaded_prompt

PROMPT_REFERENCE_SHA256 = "f4a0d39f71685aef2f20cc862dafe4280cf59fac7b7c3739ab078bbaf0b04662"


def test_prompt_has_stable_version_hash_and_required_role_boundaries():
    snapshot = load_prompt()
    normalized = snapshot.text.casefold()

    assert snapshot.version == "1.10.0"
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
