"""Comando ensaia-validar: roda a validação em todos os casos de estudo.
Compara com os valores publicados e grava os resultados de cada caso.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast, get_args

import yaml

from ensaia import __version__
from ensaia.core.design import Fator, Planejamento, termos_do_modelo
from ensaia.core.pipeline import analisar
from ensaia.core.results import (
    SCHEMA_VERSION,
    AnalysisResult,
    Sentido,
    TermoErro,
    TipoPlanejamento,
)
from ensaia.io.readers import ler_dados
from ensaia.validation import metrics

RAIZ_CASOS = Path(__file__).resolve().parents[3] / "casos_de_estudo"

# α fixado no §4.3(b) e na ADR 0003.
ALFA = metrics.ALFA_SIGNIFICANCIA


def listar_casos(raiz: Path = RAIZ_CASOS) -> list[Path]:
    """Casos prontos para rodar, sem modelo nem rascunhos."""
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


def validar_caso(caso: Path, *, executado_em: str | None = None) -> dict[str, Any]:
    """Roda a análise de um caso e aplica as métricas do §4.3."""
    referencia = _ler_referencia(caso / "referencia.yaml")
    dados = ler_dados(caso / "dados.csv")
    planejamento = _montar_planejamento(referencia)
    fatores = planejamento.nomes_fatores
    termos = _termos_publicados(referencia, fatores)
    _exigir_grandeza_suportada(caso.name, referencia)

    respostas = referencia.get("respostas")
    if not isinstance(respostas, dict) or not respostas:
        raise ValueError(f"{caso.name}: 'respostas' deve conter ao menos uma resposta.")

    # O mesmo pipeline da tela, com parâmetros do referencia.yaml.
    try:
        analise: AnalysisResult = analisar(
            dados,
            planejamento,
            termos,
            [str(r) for r in respostas],
            versao_ensaia=__version__,
            alfa=ALFA,
            executado_em=executado_em,
            # Termo de erro do artigo (Statistica costuma usar o erro puro).
            termo_erro=_termo_erro(referencia),
            objetivos=_objetivos(referencia),
        )
    except ValueError as erro:
        raise ValueError(f"{caso.name}: {erro}") from erro

    metricas, condicao = _aplicar_metricas(analise, referencia, planejamento)

    return {
        "caso": caso.name,
        "termos": termos,
        "analise": analise,
        "metricas": metricas,
        "condicao_otima": condicao,
    }


def _aplicar_metricas(
    analise: AnalysisResult,
    referencia: dict[str, Any],
    planejamento: Planejamento,
) -> tuple[dict[str, dict[str, Any]], metrics.ResultadoCondicaoOtima]:
    """Aplica os critérios (a) a (d) contra os valores publicados."""
    respostas_ref = referencia["respostas"]
    por_resposta: dict[str, dict[str, Any]] = {}
    for nome_resposta, ref in respostas_ref.items():
        resposta = str(nome_resposta)
        coefs_ref = {
            str(t): float(v) for t, v in (ref.get("coeficientes") or {}).items()
        }
        # Termos sem significância publicada ficam fora da taxa.
        sig_ref = {
            str(t): bool(v)
            for t, v in (ref.get("significancia") or {}).items()
            if v is not None
        }
        por_resposta[resposta] = {
            "erro_coeficientes": metrics.erro_relativo_coeficientes(
                analise, resposta, coefs_ref
            ),
            "concordancia_significancia": metrics.concordancia_significancia(
                analise, resposta, sig_ref
            ),
            "comparacao_r2": metrics.comparacao_r2(
                analise, resposta, ref.get("r2"), ref.get("r2_ajustado")
            ),
        }

    coordenadas_ref = (referencia.get("condicao_otima") or {}).get("coordenadas") or {}
    faixas = {f.nome: (f.minimo, f.maximo) for f in planejamento.fatores}
    condicao = metrics.diferenca_condicao_otima(
        analise,
        {str(f): float(v) for f, v in coordenadas_ref.items()},
        faixas,
    )
    return por_resposta, condicao


def _exigir_grandeza_suportada(nome_caso: str, referencia: dict[str, Any]) -> None:
    """Recusa casos que publicam efeitos em vez de coeficientes."""
    grandeza = referencia.get("grandeza_reportada", "coeficiente")
    if grandeza == "efeito":
        raise ValueError(
            f"{nome_caso}: grandeza_reportada 'efeito' ainda não é suportada. "
            "A conversão efeito→coeficiente não é um fator único de 2 para todos "
            "os termos; implemente antes de comparar."
        )
    if grandeza != "coeficiente":
        raise ValueError(
            f"{nome_caso}: grandeza_reportada inválida: {grandeza!r}. "
            "Use 'coeficiente' ou 'efeito'."
        )


def _ler_referencia(caminho: Path) -> dict[str, Any]:
    """Lê o referencia.yaml do caso."""
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
    """Monta o planejamento a partir do referencia.yaml."""
    tipo = referencia.get("tipo_planejamento")
    if tipo not in get_args(TipoPlanejamento):
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

    # Sem alfa_axial, o composto central usa o α rotacional.
    alfa = referencia.get("alfa_axial")
    if alfa is None and tipo == "composto_central":
        alfa = (2 ** len(fatores)) ** 0.25
    return Planejamento(
        tipo=cast(TipoPlanejamento, tipo),
        fatores=fatores,
        alfa_axial=float(alfa) if alfa is not None else None,
    )


def _objetivos(referencia: dict[str, Any]) -> dict[str, Sentido] | None:
    """Sentido da otimização de cada resposta."""
    bruto = (referencia.get("condicao_otima") or {}).get("objetivos")
    if not bruto:
        return None
    validos = get_args(Sentido)
    objetivos: dict[str, Sentido] = {}
    for resposta, sentido in bruto.items():
        if sentido not in validos:
            raise ValueError(
                f"Objetivo inválido para {resposta!r}: {sentido!r}. Use {validos}."
            )
        objetivos[str(resposta)] = cast(Sentido, sentido)
    return objetivos


def _termo_erro(referencia: dict[str, Any]) -> TermoErro:
    """Termo de erro pedido pelo caso."""
    termo = referencia.get("termo_erro", "residuo")
    if termo not in get_args(TermoErro):
        raise ValueError(
            f"termo_erro inválido: {termo!r}. Use 'residuo' ou 'erro_puro'."
        )
    return cast(TermoErro, termo)


def _termos_publicados(referencia: dict[str, Any], fatores: list[str]) -> list[str]:
    """Termos do modelo do caso (padrão: quadrático completo)."""
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


def gravar_resultados(caso: Path, resultado: dict[str, Any]) -> list[Path]:
    """Grava o resultado e as métricas em JSON na pasta do caso."""
    destino = caso / "resultados"
    destino.mkdir(exist_ok=True)

    analise: AnalysisResult = resultado["analise"]
    arquivo_analise = destino / "analysis_result.json"
    arquivo_analise.write_text(analise.to_json() + "\n", encoding="utf-8")

    arquivo_metricas = destino / "metricas_validacao.json"
    arquivo_metricas.write_text(
        json.dumps(_metricas_para_dict(resultado), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    arquivos = [arquivo_analise, arquivo_metricas]

    relatorio_md = _relatorio_m0_md(resultado)
    if relatorio_md is not None:
        arquivo_relatorio = destino / "relatorio_m0.md"
        arquivo_relatorio.write_text(relatorio_md + "\n", encoding="utf-8")
        arquivos.append(arquivo_relatorio)
    return arquivos


def _relatorio_m0_md(resultado: dict[str, Any]) -> str | None:
    """Relatório em texto sem IA do caso, em Markdown."""
    try:
        from ensaia.ai.report import gerar_relatorio
    except ImportError:
        return None

    relatorio = gerar_relatorio(resultado["analise"], modo="m0")
    cabecalho = (
        f"# {resultado['caso']} — relatório textual (modo M0, sem IA)\n\n"
        "> Texto gerado automaticamente a partir dos fatos verificados pelo "
        "núcleo determinístico. É o modo M0 (sem IA): offline e sempre fiel — "
        "nenhum número foi redigido por um modelo de linguagem.\n\n"
    )
    return cabecalho + relatorio.texto_completo()


def _metricas_para_dict(resultado: dict[str, Any]) -> dict[str, Any]:
    """Métricas do §4.3 como dicionário para JSON."""
    return {
        "caso": resultado["caso"],
        "schema_version": SCHEMA_VERSION,
        "criterios": {
            "a_erro_relativo_coeficientes_pct": metrics.TOLERANCIA_ERRO_RELATIVO,
            "b_alfa_significancia": metrics.ALFA_SIGNIFICANCIA,
            "c_tolerancia_r2": metrics.TOLERANCIA_R2,
        },
        "respostas": {
            resposta: {chave: asdict(valor) for chave, valor in metricas.items()}
            for resposta, metricas in resultado["metricas"].items()
        },
        "condicao_otima": asdict(resultado["condicao_otima"]),
        "dentro_das_tolerancias": _dentro_das_tolerancias(resultado),
    }


def _dentro_das_tolerancias(resultado: dict[str, Any]) -> bool:
    """Diz se todas as respostas passam em (a), (b) e (c)."""
    for metricas in resultado["metricas"].values():
        if metricas["erro_coeficientes"].proporcao_dentro_tolerancia < 1.0:
            return False
        if metricas["concordancia_significancia"].taxa_concordancia < 1.0:
            return False
        if not metricas["comparacao_r2"].dentro_tolerancia:
            return False
    return True


def main(argv: list[str] | None = None) -> int:
    # Força UTF-8 no console do Windows.
    """Ponto de entrada do comando ensaia-validar."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        prog="ensaia-validar",
        description="Valida o pipeline do EnsaIA contra os casos de estudo publicados.",
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
    todos_ok = True
    for caso in casos:
        print(f"\n=== {caso.name} ===")
        resultado = validar_caso(caso)
        print(f"Termos: {', '.join(resultado['termos'])}")
        for resposta, metricas in resultado["metricas"].items():
            ajuste = resultado["analise"].ajuste(resposta)
            erro = metricas["erro_coeficientes"]
            r2 = metricas["comparacao_r2"]
            sig = metricas["concordancia_significancia"]
            erro_max = (
                f"{erro.erro_relativo_maximo_pct:.2f}%"
                if erro.erro_relativo_maximo_pct is not None
                else "n/d"
            )
            print(
                f"{resposta}: R²={ajuste.r2:.4f} (Δ="
                f"{_fmt(r2.diferenca_r2)}); "
                f"erro máx coef={erro_max}; "
                f"concordância sig={sig.n_concordantes}/{sig.n_total}"
            )
        ok = _dentro_das_tolerancias(resultado)
        todos_ok = todos_ok and ok
        veredito = "dentro das tolerâncias" if ok else "FORA — ver JSON"
        print(f"§4.3 (a,b,c): {veredito}")
        condicao = resultado["condicao_otima"]
        if condicao.aplicavel:
            # (d) não tem tolerância na spec: é registrado e discutido.
            partes = [
                f"{d.fator} {d.valor_ensaia:.4g} vs {d.valor_referencia:.4g}"
                + (
                    f" ({d.diferenca_pct_faixa:.1f}% da faixa)"
                    if d.diferenca_pct_faixa is not None
                    else ""
                )
                for d in condicao.diferencas
            ]
            print("§4.3 (d) condição ótima: " + "; ".join(partes))
        arquivos = gravar_resultados(caso, resultado)
        print("Gravado: " + ", ".join(str(a.relative_to(caso)) for a in arquivos))

    return 0 if todos_ok else 2


def _fmt(valor: float | None) -> str:
    """Número com 4 casas ou n/d."""
    return f"{valor:.4f}" if valor is not None else "n/d"


if __name__ == "__main__":
    raise SystemExit(main())
