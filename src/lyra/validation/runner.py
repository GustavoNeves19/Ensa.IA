"""Executa a validação sobre todos os casos de estudo — §4.3 do pré-projeto.

Ponto de entrada: `uv run lyra-validar`.

Este é o script que produz o capítulo de resultados do TCC. A saída dele
precisa ser reproduzível a partir do repositório limpo: mesmos casos, mesmo
código, mesmas tabelas.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from lyra.core.design import Fator, Planejamento, termos_do_modelo
from lyra.core.model import ajustar_ols, matriz_modelo
from lyra.io.readers import ler_dados

RAIZ_CASOS = Path(__file__).resolve().parents[3] / "casos_de_estudo"


def listar_casos(raiz: Path = RAIZ_CASOS) -> list[Path]:
    """Casos aptos à execução, excluindo template e transcrições em rascunho."""
    if not raiz.exists():
        return []
    return sorted(
        d
        for d in raiz.iterdir()
        if d.is_dir()
        and not d.name.startswith("_")
        and (d / "referencia.yaml").exists()
        and _ler_referencia(d / "referencia.yaml").get("status") != "rascunho"
    )


def validar_caso(caso: Path) -> dict[str, Any]:
    """Executa o ajuste OLS publicado para um caso de estudo.

    Esta etapa implementa a entrada oficial e o ajuste determinístico. As
    métricas do §4.3 e os JSONs de evidência serão acrescentados em seguida,
    para não chamar uma reprodução manual de validação automatizada final.

    Quando `referencia.yaml` contém `termos_modelo`, a lista é usada sem
    alterações. Isso é essencial para artigos que selecionaram um modelo
    reduzido, como o 2FI de Go et al. (2022).
    """
    referencia = _ler_referencia(caso / "referencia.yaml")
    dados = ler_dados(caso / "dados.csv")
    planejamento = _montar_planejamento(referencia)
    fatores = planejamento.nomes_fatores
    termos = _termos_publicados(referencia, fatores)

    respostas = referencia.get("respostas")
    if not isinstance(respostas, dict) or not respostas:
        raise ValueError(f"{caso.name}: 'respostas' deve conter ao menos uma resposta.")

    colunas_exigidas = set(fatores) | set(respostas)
    ausentes = sorted(colunas_exigidas - set(dados.columns))
    if ausentes:
        raise ValueError(
            f"{caso.name}: colunas ausentes em dados.csv: {ausentes}. "
            f"Disponíveis: {list(dados.columns)}."
        )

    ajustes: dict[str, Any] = {}
    for nome_resposta in respostas:
        resposta = str(nome_resposta)
        y = pd.to_numeric(dados[resposta], errors="coerce")
        if y.isna().any():
            linhas = (y.index[y.isna()] + 2).tolist()
            raise ValueError(
                f"{caso.name}: a resposta {resposta!r} tem valores ausentes ou "
                f"não numéricos nas linhas CSV {linhas}."
            )
        matriz = matriz_modelo(dados, planejamento, termos, codificar=True)
        ajustes[resposta] = ajustar_ols(matriz, y)

    return {
        "caso": caso.name,
        "planejamento": planejamento,
        "termos": termos,
        "ajustes": ajustes,
    }


def _ler_referencia(caminho: Path) -> dict[str, Any]:
    if not caminho.exists():
        raise FileNotFoundError(f"Referência do caso não encontrada: {caminho}")
    with caminho.open(encoding="utf-8") as arquivo:
        referencia = yaml.safe_load(arquivo)
    if not isinstance(referencia, dict):
        raise ValueError(
            f"{caminho}: o YAML precisa conter um objeto no nível superior."
        )
    return referencia


def _montar_planejamento(referencia: dict[str, Any]) -> Planejamento:
    tipo = referencia.get("tipo_planejamento")
    tipos_validos = {
        "fatorial_completo",
        "fatorial_fracionado",
        "composto_central",
        "box_behnken",
        "desconhecido",
    }
    if tipo not in tipos_validos:
        raise ValueError(f"tipo_planejamento inválido: {tipo!r}.")
    fatores_ref = referencia.get("fatores")
    if not isinstance(fatores_ref, dict) or not fatores_ref:
        raise ValueError("'fatores' deve conter os nomes e faixas dos fatores.")

    fatores: list[Fator] = []
    for nome, faixa in fatores_ref.items():
        if not isinstance(faixa, dict):
            raise ValueError(f"Fator {nome!r} deve ser um objeto com mínimo e máximo.")
        try:
            minimo = float(faixa["minimo"])
            maximo = float(faixa["maximo"])
        except (KeyError, TypeError, ValueError) as erro:
            raise ValueError(
                f"Fator {nome!r} precisa de mínimo e máximo numéricos."
            ) from erro
        fatores.append(Fator(nome, minimo, maximo, str(faixa.get("unidade", ""))))

    return Planejamento(tipo=tipo, fatores=fatores)


def _termos_publicados(referencia: dict[str, Any], fatores: list[str]) -> list[str]:
    termos = referencia.get("termos_modelo")
    if termos is None:
        return termos_do_modelo(fatores)
    if (
        not isinstance(termos, list)
        or not termos
        or not all(isinstance(t, str) for t in termos)
    ):
        raise ValueError("'termos_modelo' deve ser uma lista não vazia de strings.")
    return termos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lyra-validar",
        description="Valida o pipeline do LYRA contra os casos de estudo publicados.",
    )
    parser.add_argument(
        "--caso",
        help="Nome de um caso específico. Omitido, roda todos.",
    )
    parser.add_argument(
        "--raiz",
        type=Path,
        default=RAIZ_CASOS,
        help="Diretório dos casos de estudo.",
    )
    args = parser.parse_args(argv)

    casos = listar_casos(args.raiz)
    if args.caso:
        casos = [c for c in casos if c.name == args.caso]
        if not casos:
            print(f"Caso {args.caso!r} não encontrado em {args.raiz}", file=sys.stderr)
            return 1

    if not casos:
        print(
            "Nenhum caso de estudo cadastrado ainda.\n"
            "Comece copiando o template:\n"
            "    cp -r casos_de_estudo/_template casos_de_estudo/meu-caso\n"
            "Ver casos_de_estudo/README.md.",
            file=sys.stderr,
        )
        return 1

    print(f"Casos encontrados: {', '.join(c.name for c in casos)}")
    for caso in casos:
        print(f"\n=== {caso.name} ===")
        resultado = validar_caso(caso)
        print(f"Termos: {', '.join(resultado['termos'])}")
        for resposta, ajuste in resultado["ajustes"].items():
            print(
                f"{resposta}: R²={ajuste.r2:.4f}; "
                f"R² ajustado={ajuste.r2_ajustado:.4f}; "
                f"SSR={ajuste.soma_quadrados_residual:.4f}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
