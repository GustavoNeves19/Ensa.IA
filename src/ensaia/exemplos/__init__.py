"""Dados de exemplo (RF-18, US-04): experimentos públicos, já validados.

São os mesmos dados dos casos de estudo da validação, publicados em acesso
aberto e citados abaixo. Servem para o usuário explorar o EnsaIA antes de usar
os próprios dados — e para o professor mostrar uma análise completa em aula.

Vazio por ora: os dois exemplos que existiam (Box-Behnken) saíram do escopo
quando o EnsaIA passou a reconhecer só o DCCR (ADR 0013). Falta curar um
exemplo DCCR público para repor — ver `casos_de_estudo/tylosin-photo-fenton`
(rascunho, aguardando transcrição) ou os outros candidatos CCD listados em
`docs/pesquisa/casos-de-estudo-candidatos.md`.
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


EXEMPLOS: dict[str, Exemplo] = {}


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
