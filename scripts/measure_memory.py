r"""Confere as metas de memória do EnsaIA (RNF-01, spec §16.2).

Metas do RNF-01: **ocioso ≤ 150 MB** e **pico ≤ 300 MB** numa análise completa
com PDF. Aqui "MB" é MiB (2^20 bytes), a mesma unidade do limite de memória do
Docker (``mem_limit: 512m``) e dos planos de hospedagem de 512 MB.

## O que é medido, e como (leia antes de citar os números)

São duas medições, em dois processos diferentes:

(a) **Ocioso.** Sobe o servidor de verdade, do mesmo jeito que a imagem Docker
    sobe (``uvicorn ensaia.app.main:app``, 1 worker, sem reload), numa porta
    livre; espera ``GET /health`` responder, aguarda alguns segundos para o
    processo assentar e lê o RSS do processo do servidor com ``psutil``. Também
    anota quanto tempo o servidor levou para responder (RNF-12: ≤ 5 s).

(b) **Pico.** A análise completa NÃO é disparada dentro do servidor: a
    interface é NiceGUI e o fluxo "enviar planilha, analisar, baixar PDF" só
    existe via navegador/websocket, sem uma rota HTTP que o acione de fora.
    Então o pico é medido num **processo Python separado** (modo ``--carga``)
    que:

    1. importa ``ensaia.app.main``, o que carrega a mesma pilha do servidor
       (FastAPI, NiceGUI, Uvicorn, núcleo, telas);
    2. lê ``casos_de_estudo/mazloomi-2023-zif67-metronidazol/dados.csv`` com
       ``ensaia.io.readers.ler_dados``;
    3. monta o ``Planejamento`` e escolhe os termos do mesmo jeito que
       ``ensaia.ui.analise._rodar_analise`` (mapeamento padrão da tela: colunas
       numéricas viram fatores e a última vira resposta);
    4. roda ``ensaia.core.pipeline.analisar``, gera o texto fiel (modo M0) e o
       PDF com ``ensaia.report.gerar_pdf``, que carrega matplotlib e fpdf2.

    O pico é o maior RSS desse processo: o valor de alta-d'água do sistema
    operacional (``VmHWM`` no Linux, ``peak_wset`` no Windows) e, como
    conferência, o maior valor amostrado de fora a cada 20 ms.

**Limitação:** o pico (b) não inclui o custo de uma sessão NiceGUI aberta no
navegador (árvore de componentes, websocket, gráficos ECharts). A spec (§16.1)
estima cada sessão em < 5 MB; o número de (b) é, portanto, uma aproximação do
pico real do servidor, não uma medição dentro dele. O número de referência é o
do Linux (CI e contêiner); no Windows o RSS é o *working set* e os valores
diferem.

## Como rodar

    uv run python scripts/measure_memory.py          # precisa do extra [dev]

Sai com código 0 se as duas metas forem atendidas, 1 se alguma passar do
limite e 2 se a medição em si falhar (servidor não subiu, por exemplo).

O modo ``--carga`` sozinho não precisa do ``psutil`` no Linux (lê o
``/proc``), então também roda dentro da imagem de produção, que não tem o extra
dev. O CI usa isso para medir o pico na própria imagem:

    docker run --rm -v "$PWD:/work:ro" -w /work ensaia:ci \
        python scripts/measure_memory.py --carga
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import psutil

RAIZ = Path(__file__).resolve().parents[1]
CASO = RAIZ / "casos_de_estudo" / "mazloomi-2023-zif67-metronidazol" / "dados.csv"

MIB = 1024 * 1024
LIMITE_OCIOSO_MIB = 150
LIMITE_PICO_MIB = 300
LIMITE_INICIALIZACAO_S = 5.0  # RNF-12; informativo, não reprova

ESPERA_HEALTH_S = 120.0  # folga para máquinas lentas; o RNF-12 é medido à parte
ASSENTAR_S = 3.0
AMOSTRA_S = 0.02


def _ambiente() -> dict[str, str]:
    """Ambiente dos subprocessos: o mesmo da imagem Docker (spec §16.2)."""
    env = dict(os.environ)
    env.setdefault("MALLOC_ARENA_MAX", "2")
    env.setdefault("MPLBACKEND", "Agg")
    env["PYTHONUNBUFFERED"] = "1"
    # Funciona com o pacote instalado (uv sync) e também só com o código-fonte.
    src = str(RAIZ / "src")
    env["PYTHONPATH"] = os.pathsep.join(p for p in (src, env.get("PYTHONPATH")) if p)
    return env


def _porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        porta: int = s.getsockname()[1]
        return porta


def _rss_arvore(processo: psutil.Process) -> int:
    """RSS do processo somado ao dos filhos (com 1 worker não deve haver filhos)."""
    import psutil

    total = processo.memory_info().rss
    for filho in processo.children(recursive=True):
        with contextlib.suppress(psutil.NoSuchProcess):
            total += filho.memory_info().rss
    return total


def medir_ocioso() -> tuple[float, float]:
    """Sobe o servidor, espera o /health e devolve (RSS ocioso em MiB, segundos)."""
    import psutil

    porta = _porta_livre()
    comando = [
        sys.executable,
        "-m",
        "uvicorn",
        "ensaia.app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(porta),
        "--workers",
        "1",
        "--log-level",
        "warning",
    ]
    inicio = time.perf_counter()
    servidor = subprocess.Popen(comando, env=_ambiente(), cwd=RAIZ)
    try:
        url = f"http://127.0.0.1:{porta}/health"
        while True:
            if servidor.poll() is not None:
                codigo = servidor.returncode
                raise RuntimeError(
                    f"o servidor encerrou antes de responder ({codigo=})"
                )
            try:
                with urllib.request.urlopen(url, timeout=1) as resposta:
                    if resposta.status == 200:
                        break
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                pass
            if time.perf_counter() - inicio > ESPERA_HEALTH_S:
                raise RuntimeError(f"/health não respondeu em {ESPERA_HEALTH_S:.0f} s")
            time.sleep(0.1)
        inicializacao = time.perf_counter() - inicio
        time.sleep(ASSENTAR_S)
        rss = _rss_arvore(psutil.Process(servidor.pid))
        return rss / MIB, inicializacao
    finally:
        servidor.terminate()
        try:
            servidor.wait(timeout=10)
        except subprocess.TimeoutExpired:
            servidor.kill()
            servidor.wait()


def medir_pico() -> tuple[float, float]:
    """Roda a carga num processo separado; devolve (RSS após importar, pico) em MiB."""
    import psutil

    carga = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--carga"],
        env=_ambiente(),
        cwd=RAIZ,
        stdout=subprocess.PIPE,
        text=True,
    )
    amostrado = 0
    parar = threading.Event()

    def amostrar() -> None:
        nonlocal amostrado
        try:
            processo = psutil.Process(carga.pid)
            while not parar.is_set():
                amostrado = max(amostrado, processo.memory_info().rss)
                time.sleep(AMOSTRA_S)
        except psutil.Error:
            pass  # o processo terminou entre duas amostras

    amostrador = threading.Thread(target=amostrar, daemon=True)
    amostrador.start()
    saida, _ = carga.communicate()
    parar.set()
    amostrador.join()
    if carga.returncode != 0:
        raise RuntimeError(f"a carga de análise falhou (código {carga.returncode})")
    relatorio = json.loads(saida.strip().splitlines()[-1])
    pico = max(relatorio["pico"], amostrado)
    return relatorio["apos_importar"] / MIB, pico / MIB


def _status_proc(campo: str) -> int | None:
    """Lê um campo de memória de /proc/self/status, em bytes (None fora do Linux)."""
    status = Path("/proc/self/status")
    if not status.exists():
        return None
    for linha in status.read_text().splitlines():
        if linha.startswith(f"{campo}:"):
            return int(linha.split()[1]) * 1024  # vem em kB
    return None


def _rss_atual() -> int:
    """RSS atual deste processo, em bytes."""
    valor = _status_proc("VmRSS")
    if valor is None:
        import psutil

        valor = psutil.Process().memory_info().rss
    return valor


def _pico_proprio() -> int:
    """Maior RSS que este processo já atingiu, segundo o sistema operacional."""
    valor = _status_proc("VmHWM")  # Linux: "high water mark" do RSS
    if valor is not None:
        return valor
    import psutil

    info = psutil.Process().memory_info()
    pico: int = getattr(info, "peak_wset", 0)  # Windows
    if not pico and sys.platform != "win32":
        import resource  # Unix sem /proc (macOS): ru_maxrss em bytes

        pico = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return max(pico, info.rss)


def executar_carga() -> None:
    """Corpo do processo de carga (b): app + análise completa + PDF."""
    import ensaia.app.main  # noqa: F401 (carrega a mesma pilha do servidor)

    apos_importar = _rss_atual()

    from ensaia import __version__
    from ensaia.ai.report import gerar_relatorio
    from ensaia.core.design import (
        Fator,
        Planejamento,
        detectar_tipo,
        termos_do_modelo,
    )
    from ensaia.core.pipeline import analisar
    from ensaia.io.readers import ler_dados
    from ensaia.report import gerar_pdf

    tabela = ler_dados(CASO)
    numericas = [c for c in tabela.colunas if tabela.e_numerica(c)]
    fatores, respostas = numericas[:-1], numericas[-1:]

    # Mesma montagem de ensaia.ui.analise._rodar_analise / _escolher_termos.
    objetos = [
        Fator(nome, float(tabela.coluna(nome).min()), float(tabela.coluna(nome).max()))
        for nome in fatores
    ]
    niveis = {nome: list(tabela.coluna(nome)) for nome in fatores}
    tipo = detectar_tipo(niveis, len(tabela))
    planejamento = Planejamento(tipo=tipo, fatores=objetos)
    quadraticos = tipo != "fatorial_completo"
    candidatos = [
        termos_do_modelo(fatores, incluir_quadraticos=quadraticos, grau_interacao=2),
        termos_do_modelo(fatores, incluir_quadraticos=False, grau_interacao=2),
        termos_do_modelo(fatores, incluir_quadraticos=False, grau_interacao=1),
    ]
    termos = next((t for t in candidatos if len(t) < len(tabela)), candidatos[-1])

    analise = analisar(
        tabela, planejamento, termos, respostas, versao_ensaia=__version__
    )
    texto = gerar_relatorio(analise, modo="m0")
    pdf = gerar_pdf(analise, texto, gerado_em="01/01/2026 00:00")
    if not pdf.startswith(b"%PDF"):
        raise RuntimeError("gerar_pdf não devolveu um PDF")

    print(json.dumps({"apos_importar": apos_importar, "pico": _pico_proprio()}))


def main() -> int:
    if "--carga" in sys.argv[1:]:
        executar_carga()
        return 0

    for fluxo in (sys.stdout, sys.stderr):
        if isinstance(fluxo, io.TextIOWrapper):
            fluxo.reconfigure(encoding="utf-8")  # acentos no console do Windows
    versao = sys.version.split()[0]
    print(f"Python {versao} em {sys.platform}; caso: {CASO.parent.name}")
    try:
        ocioso, inicializacao = medir_ocioso()
        base, pico = medir_pico()
    except Exception as erro:
        print(f"ERRO: a medição falhou: {erro}", file=sys.stderr)
        return 2

    linhas = [
        ("Servidor ocioso (após /health)", ocioso, LIMITE_OCIOSO_MIB),
        ("Processo de carga após importar o app", base, None),
        ("Pico: análise completa + PDF", pico, LIMITE_PICO_MIB),
    ]
    print()
    print(f"{'Medição':<40} {'RSS (MiB)':>10} {'Meta':>10}  Situação")
    print("-" * 74)
    reprovou = False
    for nome, valor, limite in linhas:
        if limite is None:
            meta, situacao = "-", "informativo"
        else:
            meta = f"<= {limite}"
            ok = valor <= limite
            reprovou |= not ok
            situacao = "ok" if ok else "ACIMA DA META"
        print(f"{nome:<40} {valor:>10.1f} {meta:>10}  {situacao}")
    situacao_inicio = "ok" if inicializacao <= LIMITE_INICIALIZACAO_S else "lento"
    print(
        f"{'Inicialização até o /health (s)':<40} {inicializacao:>10.2f} "
        f"{'<= ' + str(LIMITE_INICIALIZACAO_S):>10}  {situacao_inicio} (informativo)"
    )
    print()
    print("RNF-01 atendido." if not reprovou else "RNF-01 NÃO atendido.")
    return 1 if reprovou else 0


if __name__ == "__main__":
    sys.exit(main())
