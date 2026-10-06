# Fontes do relatório

Arquivos **DejaVu Sans** (regular, negrito, oblíquo) embutidos no pacote para que
o relatório PDF renderize os acentos do português e os símbolos dos fatos
(`≥`, `²`, `−`, `α`) de forma idêntica em qualquer máquina, sem depender das
fontes do sistema.

- **Origem:** projeto DejaVu Fonts — <https://dejavu-fonts.github.io/>
- **Licença:** livre e permissiva (deriva da Bitstream Vera License, com a
  Public Domain Dedication da Arev). Permite uso, redistribuição e embutimento,
  inclusive comercial. O único dever é não renomear a fonte para "DejaVu" após
  modificá-la — não a modificamos.

A troca da fonte do relatório é feita em um único lugar (`report/theme.py`),
então substituir estes arquivos por outra família Unicode é direto.
