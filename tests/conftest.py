"""Configuração compartilhada dos testes."""

from __future__ import annotations

import pytest


@pytest.fixture
def dados_fatorial_2k():
    """Fatorial 2² com pontos centrais — o menor caso útil de verdade.

    Tem repetição no centro, então permite testar falta de ajuste; e tem
    curvatura, então o termo quadrático é estimável.
    """
    import pandas as pd

    return pd.DataFrame(
        {
            "temperatura": [40, 80, 40, 80, 60, 60, 60],
            "ph": [3.0, 3.0, 9.0, 9.0, 6.0, 6.0, 6.0],
            "rendimento": [62.1, 71.5, 58.9, 77.2, 80.4, 79.8, 80.9],
        }
    )
