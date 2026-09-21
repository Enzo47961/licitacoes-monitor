# Monitor Inteligente e Agregador de Oportunidades do PNCP

MVP de um sistema que permite empresas se cadastrarem, configurarem filtros de interesse
para licitações públicas e receberem alertas automatizados via Telegram quando novos
editais compatíveis forem publicados no **PNCP (Portal Nacional de Contratações Públicas)**.

## Estrutura do projeto

```
licitacoes/
├── app.py                  # Interface Streamlit (cadastro + dashboard)
├── worker.py                # Worker standalone para execução agendada (cron)
├── requirements.txt
├── .env.example
├── database/
│   └── db.py                # Configuração do SQLAlchemy (engine, sessão, init_db)
├── models/
│   └── models.py             # Modelos: EmpresaPerfil, EditalNotificado
├── services/
│   └── pncp_service.py        # Consumo da API do PNCP, matching e alertas no Telegram
└── data/
    └── licitacoes.db           # Banco SQLite (criado automaticamente na 1ª execução)
```

## Tecnologias

- **Backend:** Python (script modular)
- **Frontend:** Streamlit
- **Banco de Dados:** SQLite via SQLAlchemy
- **Integrações:** API REST pública do PNCP + Telegram Bot API

## Como executar

1. Crie um ambiente virtual e instale as dependências:

   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   pip install -r requirements.txt
   ```

2. (Opcional) copie `.env.example` para `.env` e preencha as credenciais padrão do Telegram.

3. Rode a interface:

   ```bash
   streamlit run app.py
   ```

4. Acesse `http://localhost:8501`, use o botão **"Carregar Perfil de Exemplo (TI)"** na aba
   de Cadastro para testar rapidamente, ou preencha um perfil próprio e salve.

5. Na aba **Dashboard de Oportunidades Filtradas**, selecione a empresa e clique em
   **"Buscar Editais Agora"** para consultar o PNCP, aplicar o matching e ver os resultados
   em tabela e em cards.

## Execução automática (worker)

Para rodar o monitoramento periodicamente sem abrir o Streamlit (ex: via cron ou
Agendador de Tarefas do Windows), use:

```bash
python worker.py
```

Isso varre o PNCP para todas as empresas cadastradas, registra editais inéditos no banco
(evitando notificações duplicadas) e envia os alertas configurados no Telegram.

## Como criar um Bot do Telegram (para os alertas)

1. Fale com [@BotFather](https://t.me/BotFather) no Telegram e crie um bot com `/newbot`.
2. Copie o **token** gerado e cole no campo "Token do Bot" ao cadastrar o perfil.
3. Envie uma mensagem qualquer para o seu bot e acesse
   `https://api.telegram.org/bot<TOKEN>/getUpdates` para descobrir o seu `chat_id`.
4. Preencha o `chat_id` no cadastro do perfil.

## Observações sobre a API do PNCP

O serviço `pncp_service.py` consulta o endpoint público
`https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao`, filtrando por modalidade de
contratação (Pregão Eletrônico e Dispensa de Licitação, por padrão) e por data de publicação.
Ajuste `MODALIDADES_PADRAO` em `services/pncp_service.py` conforme a necessidade.
