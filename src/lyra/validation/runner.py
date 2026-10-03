"""Executa a validação sobre todos os casos de estudo — §4.3 do pré-projeto.

Ponto de entrada: `uv run lyra-validar`.

Este é o script que produz o capítulo de resultados do TCC. A saída dele
precisa ser reproduzível a partir do repositório limpo: mesmos casos, mesmo
código, mesmas tabelas.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from lyra import __version__
from lyra.core.design import Fator, Planejamento, termos_do_modelo
from lyra.core.effects import extrair_coeficientes
from lyra.core.model import AjusteOLS, ajustar_ols, matriz_modelo
from lyra.core.results import (
    SCHEMA_VERSION,
    AjusteResposta,
    AnalysisResult,
    FaltaDeAjuste,
    LinhaAnova,
    MetadadosExecucao,
)
from lyra.io.readers import ler_dados
from lyra.validation import metrics

RAIZ_CASOS = Path(__file__).resolve().parents[3] / "casos_de_estudo"

# α fixado no §4.3(b) / ADR 0003. A significância do LYRA é avaliada neste
# nível e é também o nível do intervalo de confiança reportado.
ALFA = metrics.ALFA_SIGNIFICANCIA


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


def validar_caso(caso: Path, *, executado_em: str | None = None) -> dict[str, Any]:
    """Roda o pipeline determinístico num caso e aplica as métricas do §4.3.

    Monta o `AnalysisResult` a partir do ajuste OLS e compara com os valores
    publicados em `referencia.yaml` pelos critérios (a) erro relativo dos
    coeficientes, (b) concordância de significância e (c) diferença de R². O
    critério (d), condição ótima, só é avaliado quando a desejabilidade produz
    um ponto ótimo (issue #6); até lá `diferenca_condicao_otima` retorna
    inaplicável, em vez de inventar uma comparação.

    Quando `referencia.yaml` contém `termos_modelo`, a lista é usada sem
    alterações. Isso é essencial para artigos que selecionaram um modelo
    reduzido, como o 2FI de Go et al. (2022).

    `executado_em` é repassado ao resultado para rastreabilidade; fica fora da
    serialização quando None, mantendo o JSON reproduzível byte a byte em teste.
    """
    referencia = _ler_referencia(caso / "referencia.yaml")
    dados = ler_dados(caso / "dados.csv")
    planejamento = _montar_planejamento(referencia)
    fatores = planejamento.nomes_fatores
    termos = _termos_publicados(referencia, fatores)
    _exigir_grandeza_suportada(caso.name, referencia)

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

    matriz = matriz_modelo(dados, planejamento, termos, codificar=True)
    ajustes_resposta: list[AjusteResposta] = []
    avisos: list[str] = []
    for nome_resposta in respostas:
        resposta = str(nome_resposta)
        y = pd.to_numeric(dados[resposta], errors="coerce")
        if y.isna().any():
            linhas = (y.index[y.isna()] + 2).tolist()
            raise ValueError(
                f"{caso.name}: a resposta {resposta!r} tem valores ausentes ou "
                f"não numéricos nas linhas CSV {linhas}."
            )
        ajuste = ajustar_ols(matriz, y)
        ajustes_resposta.append(_ajuste_resposta(resposta, ajuste, termos, avisos))

    analise = AnalysisResult(
        tipo_planejamento=planejamento.tipo,
        fatores=fatores,
        respostas=[str(r) for r in respostas],
        ajustes=ajustes_resposta,
        metadados=MetadadosExecucao(
            versao_lyra=__version__, alfa=ALFA, executado_em=executado_em
        ),
        ponto_otimo=None,
        avisos=avisos,
    )

    metricas, condicao = _aplicar_metricas(analise, referencia, planejamento)

    return {
        "caso": caso.name,
        "termos": termos,
        "analise": analise,
        "metricas": metricas,
        "condicao_otima": condicao,
    }


def _ajuste_resposta(
    resposta: str, ajuste: AjusteOLS, termos: list[str], avisos: list[str]
) -> AjusteResposta:
    """Empacota um ajuste OLS no contrato congelado `AjusteResposta`.

    A extração de coeficientes é delegada a `effects.extrair_coeficientes`, que é
    a fonte única dessa tradução (issue #5): runner e núcleo não podem divergir
    no modo de nomear termos e marcar significância, sob pena de a métrica do
    §4.3(a) comparar coisas diferentes.
    """
    return AjusteResposta(
        resposta=resposta,
        coeficientes=extrair_coeficientes(ajuste, alfa=ALFA),
        anova=_linhas_anova(resposta, ajuste, avisos),
        r2=ajuste.r2,
        r2_ajustado=ajuste.r2_ajustado,
        falta_de_ajuste=FaltaDeAjuste(
            aplicavel=False,
            motivo_inaplicavel=(
                "Teste de falta de ajuste pertence à ANOVA (issue #4) e ainda "
                "não é calculado por esta etapa de validação."
            ),
        ),
        n_observacoes=ajuste.n_observacoes,
        graus_liberdade_residuo=ajuste.gl_residuo,
        termos_incluidos=list(termos),
    )


def _linhas_anova(
    resposta: str, ajuste: AjusteOLS, avisos: list[str]
) -> list[LinhaAnova]:
    """ANOVA Tipo II em linhas `LinhaAnova`, ou vazia se o modelo não é hierárquico."""
    try:
        tabela = ajuste.tabela_tipo2()
    except ValueError as erro:
        avisos.append(f"{resposta}: ANOVA Tipo II indisponível — {erro}")
        return []

    linhas: list[LinhaAnova] = []
    for fonte, linha in tabela.iterrows():
        sq = float(linha["soma_quadrados"])
        gl = int(linha["graus_liberdade"])
        f = linha["valor_f"]
        p = linha["valor_p"]
        linhas.append(
            LinhaAnova(
                fonte=str(fonte),
                soma_quadrados=sq,
                graus_liberdade=gl,
                quadrado_medio=sq / gl if gl else 0.0,
                valor_f=None if pd.isna(f) else float(f),
                valor_p=None if pd.isna(p) else float(p),
            )
        )
    return linhas


def _aplicar_metricas(
    analise: AnalysisResult,
    referencia: dict[str, Any],
    planejamento: Planejamento,
) -> tuple[dict[str, dict[str, Any]], metrics.ResultadoCondicaoOtima]:
    """Aplica os critérios (a)–(d) do §4.3 contra os valores publicados."""
    respostas_ref = referencia["respostas"]
    por_resposta: dict[str, dict[str, Any]] = {}
    for nome_resposta, ref in respostas_ref.items():
        resposta = str(nome_resposta)
        coefs_ref = {
            str(t): float(v) for t, v in (ref.get("coeficientes") or {}).items()
        }
        # Termos sem significância publicada (null) ficam fora da taxa: não dá
        # para concordar ou discordar de uma classificação que o artigo não deu.
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
    """A comparação do §4.3(a) é coeficiente-a-coeficiente.

    Converter efeito (−1 → +1) em coeficiente (centro → +1) só é um fator de 2
    para termos lineares e de interação em escala codificada; para o intercepto
    e termos quadráticos não é. Em vez de aplicar a regra errada em silêncio,
    falha alto até o caso que precise disso existir de fato.
    """
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


def gravar_resultados(caso: Path, resultado: dict[str, Any]) -> list[Path]:
    """Grava `resultados/analysis_result.json` e `resultados/metricas_validacao.json`.

    Separado de `validar_caso` de propósito: a validação é pura e testável sem
    tocar no disco; a gravação é o único ponto de escrita. Os JSONs são a
    evidência versionada do capítulo de resultados (passo 2 do protocolo).
    """
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
    return [arquivo_analise, arquivo_metricas]


def _metricas_para_dict(resultado: dict[str, Any]) -> dict[str, Any]:
    """Serializa as métricas do §4.3 num JSON autoexplicativo."""
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
    """Verdadeiro se todas as respostas passam nos critérios (a), (b) e (c).

    (d) fica de fora porque depende da desejabilidade (issue #6) e, até lá, é
    sempre inaplicável — exigi-lo reprovaria todo caso por algo ainda não
    implementado.
    """
    for metricas in resultado["metricas"].values():
        if metricas["erro_coeficientes"].proporcao_dentro_tolerancia < 1.0:
            return False
        if metricas["concordancia_significancia"].taxa_concordancia < 1.0:
            return False
        if not metricas["comparacao_r2"].dentro_tolerancia:
            return False
    return True


def main(argv: list[str] | None = None) -> int:
    # Console Windows em cp1252 quebra em símbolos como 'Δ' e '§'; a saída do
    # relatório é em português e usa esses caracteres, então força UTF-8.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

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
        arquivos = gravar_resultados(caso, resultado)
        print("Gravado: " + ", ".join(str(a.relative_to(caso)) for a in arquivos))

    return 0 if todos_ok else 2


def _fmt(valor: float | None) -> str:
    return f"{valor:.4f}" if valor is not None else "n/d"


if __name__ == "__main__":
    raise SystemExit(main())
