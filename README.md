# 📊 SPED Extractor

Ferramenta de linha de comando em Python para **extrair itens fiscais** de arquivos **SPED** (EFD Contribuições e EFD ICMS/IPI) e de documentos **NF-e / NFS-e** (XML), consolidando tudo em planilhas e relatórios de qualidade.

Pensada para análise fiscal: transforma arquivos SPED brutos em dados tabulares (CSV/JSON) prontos para conferência e cruzamento.

---

## ✨ O que faz

- **Lê múltiplas fontes fiscais:**
  - EFD Contribuições (PIS/COFINS)
  - EFD ICMS/IPI
  - NF-e (XML)
  - NFS-e (XML)
- **Extrai os itens** com seus tributos (PIS, COFINS, IPI, ISS, ICMS, ICMS-ST, DIFAL, etc.), NCM, NBS, origem, CFOP e demais campos.
- **Consolida** documentos e itens de todas as fontes.
- **Gera relatório de qualidade** apontando inconsistências e campos faltantes.
- **Exporta** em CSV e JSON.

---

## 📋 Pré-requisitos

- **Python 3.11+** (veja `.python-version`)
- Sem dependências externas em produção — usa apenas a biblioteca padrão. `pytest` só para desenvolvimento.

---

## 🚀 Instalação

O `Makefile` cuida do ambiente:

```bash
git clone https://github.com/felipetome/Spedv1.git
cd Spedv1

make setup      # cria o venv e instala o pacote em modo editable (com pytest)
```

Ou manualmente:

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

---

## ▶️ Como usar

1. Coloque os arquivos de entrada (SPED `.txt` e/ou XMLs de NF-e/NFS-e) numa pasta de entrada.
2. Rode o extrator:

   ```bash
   source venv/bin/activate
   python -m sped_extractor.main
   ```

3. As saídas são geradas em `saidas/`:
   - `itens_sped.csv` / `itens_sped.json` — itens extraídos com tributos
   - `documentos_sped.json` — documentos consolidados
   - `relatorio_qualidade.json` — inconsistências e campos faltantes

> Os caminhos padrão de entrada/saída ficam em `src/sped_extractor/config.py`.

> ⚠️ **Dados fiscais são sigilosos.** As pastas `saidas/` e `speds/` e todos os `*.csv` estão no `.gitignore` — não suba SPEDs ou saídas com dados reais para o repositório. Para testes, use as amostras **fictícias** em `tests/samples/` e `entradas/` ("EMPRESA TESTE").

---

## 🧪 Testes

```bash
make test        # roda o pytest
```

Os testes usam amostras fictícias em `tests/samples/` (SPED e XMLs de exemplo).

---

## 🧠 Estrutura do código

```
src/sped_extractor/
├── main.py            Ponto de entrada (CLI): orquestra leitura → consolidação → exportação
├── config.py          Caminhos padrão, defaults e configuração do relatório de qualidade
├── consolidator.py    Consolida documentos e itens das várias fontes
├── quality.py         Cálculo do relatório de qualidade
├── utils.py           Logging, arredondamento decimal e helpers
└── parsers/           Parsers por tipo de documento:
                       EFD Contribuições, EFD ICMS/IPI, NF-e (XML), NFS-e (XML)

tests/                 Testes + amostras fictícias
entradas/              Arquivos de exemplo (fictícios) para uso manual
doc.yaml               Documentação/mapeamento de campos
```

---

## 🛠️ Comandos do Makefile

| Comando | O que faz |
|---------|-----------|
| `make setup` | Cria o venv e instala o pacote (editable + dev). |
| `make test` | Roda o pytest. |
| `make lint` | Lint com `ruff`. |
| `make clean` | Remove venv, caches e artefatos de build. |
| `make help` | Lista os comandos. |

---

## 📄 Licença

Uso pessoal e educacional. Ajuste conforme a necessidade.
