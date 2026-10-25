"""Exemplos públicos de DCCR para abrir na tela (Tylosin e açaí).
Os mesmos dados dos casos de estudo, em acesso aberto e citados.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files

from ensaia.core.table import Table
from ensaia.io.readers import ler_dados_de_bytes


@dataclass(frozen=True)
class Exemplo:
    """Um exemplo: identificador, título, descrição, arquivo e citação."""

    id: str
    titulo: str
    descricao: str
    arquivo: str
    citacao: str


EXEMPLOS: dict[str, Exemplo] = {
    e.id: e
    for e in (
        Exemplo(
            id="tylosin",
            titulo="Degradação de tilosina por foto-Fenton (DCCR)",
            descricao=(
                "3 fatores (H2O2, pH, Fe2+), 20 ensaios, 6 no ponto central; "
                "resposta: remoção de TOC (%)."
            ),
            arquivo="sarrai_2016_tylosin.csv",
            citacao=(
                "SARRAI, A. E. et al. Materials, v. 9, n. 6, art. 428, 2016. "
                "DOI: 10.3390/ma9060428."
            ),
        ),
        Exemplo(
            id="acai",
            titulo="Hidrólise ácida de sementes de açaí (DCCR)",
            descricao=(
                "3 fatores (ácido sulfúrico, tempo, sólidos), 17 ensaios, 3 no "
                "ponto central; respostas: açúcares redutores totais (g/L), "
                "HMF (mg/L) e massa solubilizada (%)."
            ),
            arquivo="igreja_2023_acai.csv",
            citacao=(
                "IGREJA, W. S. et al. Molecules, v. 28, n. 18, art. 6661, 2023. "
                "DOI: 10.3390/molecules28186661."
            ),
        ),
    )
}


def conteudo_exemplo(id_: str) -> bytes:
    """Bytes do CSV de um exemplo."""
    if id_ not in EXEMPLOS:
        raise KeyError(f"Exemplo {id_!r} não existe. Disponíveis: {sorted(EXEMPLOS)}.")
    return files(__package__).joinpath(EXEMPLOS[id_].arquivo).read_bytes()


def carregar_exemplo(id_: str) -> tuple[Table, str]:
    """Table do exemplo e o nome do arquivo."""
    conteudo = conteudo_exemplo(id_)
    arquivo = EXEMPLOS[id_].arquivo
    return ler_dados_de_bytes(conteudo, arquivo), arquivo
