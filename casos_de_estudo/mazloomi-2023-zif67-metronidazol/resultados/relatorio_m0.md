# mazloomi-2023-zif67-metronidazol — relatório textual (modo M0, sem IA)

> Texto gerado automaticamente a partir dos fatos verificados pelo núcleo determinístico. É o modo M0 (sem IA): offline e sempre fiel — nenhum número foi redigido por um modelo de linguagem.

## Planejamento experimental

O delineamento é um delineamento Box-Behnken com 3 fatores ('dose_adsorvente', 'tempo_mistura', 'ph') e 1 resposta ('remocao_mnz'). A matriz experimental tem 15 ensaios.

## Modelo ajustado

O termo 'dose_adsorvente' é significativo (p = 0,0003 < 0,05). O termo 'tempo_mistura' é significativo (p = 0,0018 < 0,05). O termo 'ph' é significativo (p = 0,0012 < 0,05). O termo 'dose_adsorvente^2' é significativo (p = 0,0028 < 0,05). O termo 'tempo_mistura^2' é significativo (p = 0,0223 < 0,05). O termo 'ph^2' é significativo (p < 0,0001). 'dose_adsorvente:tempo_mistura', 'dose_adsorvente:ph', 'tempo_mistura:ph' não são significativos ao nível de 0,05.

## Qualidade do ajuste (ANOVA e R²)

O modelo explica 98,5% da variação da resposta 'remocao_mnz' (R² = 0,985; R² ajustado = 0,959). A regressão é significativa (p = 0,0005 < 0,05): F calculado = 37,27, F tabelado = 4,77, razão = 7,81. O R² de predição é 0,786.

## Diagnóstico do modelo

Não há evidência de falta de ajuste (p = 0,1547 ≥ 0,05). O teste de Shapiro-Wilk não indica desvio da normalidade dos resíduos (W = 0,942; p = 0,4113 ≥ 0,05).

## Otimização

O ponto estacionário da superfície é um máximo em dose_adsorvente = 0,893, tempo_mistura = 55,579, ph = 7,434, dentro da região experimental, com resposta prevista 99,3655. A condição ótima (em unidades reais) é dose_adsorvente = 0,893, tempo_mistura = 55,579, ph = 7,434. Nessa condição, a resposta prevista é remocao_mnz = 99,3655.
