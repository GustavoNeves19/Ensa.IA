"""Dados de exemplo (RF-18, US-04): experimentos públicos, já validados.

São os mesmos dados dos casos de estudo da validação, publicados em acesso
aberto e citados abaixo. Servem para o usuário explorar o EnsaIA antes de usar
os próprios dados — e para o professor mostrar uma análise completa em aula.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files

from ensaia.core.table import Table
from ensaia.io.readers import ler_dados_de_bytes


@dataclass(frozen=True)
class Exemplo:
    id: str
    titulo: str
    descricao: str
    arquivo: str
    citacao: str


EXEMPLOS: dict[str, Exemplo] = {
    e.id: e
    for e in (
        Exemplo(
            id="metronidazol",
            titulo="Remoção de metronidazol (Box-Behnken)",
            descricao=(
                "3 fatores (dose de adsorvente, tempo, pH), 15 ensaios, 3 no "
                "ponto central; resposta: remoção (%)."
            ),
            arquivo="mazloomi_2023_metronidazol.csv",
            citacao=(
                "MAZLOOMI, S. et al. Scientific Reports, v. 13, art. 14654, 2023. "
                "DOI: 10.1038/s41598-023-41724-y (CC BY 4.0)."
            ),
        ),
        Exemplo(
            id="levofloxacino",
            titulo="Fotodegradação de levofloxacino (Box-Behnken)",
            descricao=(
                "3 fatores (dose de catalisador, concentração, pH), 15 ensaios; "
                "resposta: eficiência de fotodegradação (%)."
            ),
            arquivo="go_2022_levofloxacino.csv",
            citacao=(
                "GO, A. D. et al. Data in Brief, v. 42, art. 108219, 2022. "
                "DOI: 10.1016/j.dib.2022.108219."
            ),
        ),
    )
}


def conteudo_exemplo(id_: str) -> bytes:
    """Bytes do CSV de um exemplo (o mesmo formato de um upload)."""
    if id_ not in EXEMPLOS:
        raise KeyError(f"Exemplo {id_!r} não existe. Disponíveis: {sorted(EXEMPLOS)}.")
    return files(__package__).joinpath(EXEMPLOS[id_].arquivo).read_bytes()


def carregar_exemplo(id_: str) -> tuple[Table, str]:
    """`Table` do exemplo e o nome do arquivo, prontos para o fluxo da tela."""
    conteudo = conteudo_exemplo(id_)
    arquivo = EXEMPLOS[id_].arquivo
    return ler_dados_de_bytes(conteudo, arquivo), arquivo
