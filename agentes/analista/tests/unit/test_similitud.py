import time

from agentes.conocimiento import similitud


def _vectorizador(lista_texto):
    tabla = {"teléfono": [1.0, 0.0], "dígitos del teléfono": [0.9, 0.1], "vigencia": [0.0, 1.0]}
    return [tabla[texto] for texto in lista_texto]


def test_similitud_maxima_compara_cada_punto_contra_todas_las_referencias_en_una_llamada():
    llamada = []

    def contar(lista_texto):
        llamada.append(list(lista_texto))
        return _vectorizador(lista_texto)

    resultado = similitud.similitud_maxima(["dígitos del teléfono", "vigencia"], ["teléfono"], vectorizador=contar)

    assert len(llamada) == 1
    assert resultado[0] > 0.99 and resultado[1] == 0.0


def test_similitud_sin_referencias_no_llama_a_pinecone():
    assert similitud.similitud_maxima(["vigencia"], [], vectorizador=lambda texto: 1 / 0) == [0.0]


def test_similitud_no_disponible_sin_clave(monkeypatch):
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)

    assert similitud.similitud_maxima(["vigencia"], ["teléfono"]) is None


def test_similitud_no_disponible_si_pinecone_falla_o_tarda():
    def fallar(lista_texto):
        raise RuntimeError("sin red")

    def tardar(lista_texto):
        time.sleep(0.3)
        return _vectorizador(lista_texto)

    assert similitud.similitud_maxima(["vigencia"], ["teléfono"], vectorizador=fallar) is None
    assert similitud.similitud_maxima(["vigencia"], ["teléfono"], vectorizador=tardar, tiempo_maximo=0.05) is None
