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

RAIZ_CASOS = Path(__file__).resolve().parents[3] / "casos_de_estudo"


def listar_casos(raiz: Path = RAIZ_CASOS) -> list[Path]:
    """Todos os diretórios de caso de estudo, exceto o template."""
    if not raiz.exists():
        return []
    return sorted(
        d
        for d in raiz.iterdir()
        if d.is_dir()
        and not d.name.startswith("_")
        and (d / "referencia.yaml").exists()
    )


def validar_caso(caso: Path) -> dict:
    """Roda o pipeline num caso e aplica as métricas do §4.3.

    TODO(#8): implementar.
        1. ler dados.csv e referencia.yaml
        2. montar Planejamento a partir da referência
        3. rodar o pipeline determinístico
        4. aplicar metrics.erro_relativo_coeficientes  (§4.3a)
                     metrics.concordancia_significancia (§4.3b)
                     metrics.comparacao_r2              (§4.3c)
                     metrics.diferenca_condicao_otima   (§4.3d)
        5. gravar em <caso>/resultados/: AnalysisResult em JSON, tabela
           comparativa, e a planilha de fidelidade a preencher (§4.3e)

    Atenção ao campo `grandeza_reportada` do referencia.yaml: se o artigo
    publica *efeitos* e o LYRA calcula *coeficientes*, é preciso converter
    antes de comparar (efeito = 2 × coeficiente em escala codificada). Sem
    isso, o erro relativo dá ~100% em toda a tabela e parece falha do
    pipeline.
    """
    raise NotImplementedError("Ver issue #8 — runner de validação.")


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
        validar_caso(caso)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
