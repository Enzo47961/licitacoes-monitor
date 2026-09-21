"""Integração com a API pública do PNCP, lógica de matching e disparo de alertas no Telegram."""
from datetime import datetime, timedelta

import requests

PNCP_BASE_URL = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

# Códigos de modalidade de contratação mais comuns (Pregão Eletrônico, Concorrência, etc.)
# Ver documentação oficial do PNCP para a lista completa.
MODALIDADES_PADRAO = [6, 8]  # 6 = Pregão Eletrônico, 8 = Dispensa de Licitação


def buscar_editais_pncp(dias_retroativos: int = 1, uf: str | None = None, pagina: int = 1) -> list[dict]:
    """
    Consulta a API pública do PNCP por contratações publicadas nos últimos `dias_retroativos` dias.

    Retorna uma lista de dicionários já normalizados com os campos usados pelo matching.
    Em caso de falha de rede/API, retorna lista vazia (fail-safe para não travar o worker).
    """
    data_final = datetime.now()
    data_inicial = data_final - timedelta(days=dias_retroativos)

    resultados = []

    for modalidade in MODALIDADES_PADRAO:
        params = {
            "dataInicial": data_inicial.strftime("%Y%m%d"),
            "dataFinal": data_final.strftime("%Y%m%d"),
            "codigoModalidadeContratacao": modalidade,
            "pagina": pagina,
            "tamanhoPagina": 50,
        }
        if uf:
            params["uf"] = uf

        try:
            resp = requests.get(PNCP_BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            corpo = resp.json()
        except (requests.RequestException, ValueError):
            continue

        for item in corpo.get("data", []):
            resultados.append(_normalizar_edital(item))

    return resultados


def _normalizar_edital(item: dict) -> dict:
    """Extrai e padroniza os campos relevantes de um item retornado pela API do PNCP."""
    orgao = (item.get("orgaoEntidade") or {}).get("razaoSocial", "Órgão não informado")
    numero_controle = item.get("numeroControlePNCP", "")
    ano = item.get("anoCompra", "")
    sequencial = item.get("sequencialCompra", "")

    link = (
        f"https://pncp.gov.br/app/editais/{item.get('orgaoEntidade', {}).get('cnpj', '')}"
        f"/{ano}/{sequencial}"
    )

    return {
        "numero_controle_pncp": numero_controle or f"{ano}-{sequencial}",
        "orgao": orgao,
        "objeto": item.get("objetoCompra", ""),
        "valor_estimado": item.get("valorTotalEstimado") or 0,
        "data_sessao": item.get("dataAberturaProposta", ""),
        "uf": (item.get("unidadeOrgao") or {}).get("ufSigla", ""),
        "link": link,
    }


def calcular_match(edital: dict, perfil) -> bool:
    """
    Verifica se um edital é compatível com o perfil de interesse da empresa,
    combinando palavras-chave positivas/negativas, UF e faixa de valor.
    """
    objeto = (edital.get("objeto") or "").lower()

    positivas = perfil.lista_palavras_positivas()
    negativas = perfil.lista_palavras_negativas()
    estados = perfil.lista_estados()

    if positivas and not any(palavra in objeto for palavra in positivas):
        return False

    if negativas and any(palavra in objeto for palavra in negativas):
        return False

    if estados and edital.get("uf") and edital["uf"] not in estados:
        return False

    valor = edital.get("valor_estimado") or 0
    if perfil.valor_minimo and valor < perfil.valor_minimo:
        return False
    if perfil.valor_maximo and perfil.valor_maximo > 0 and valor > perfil.valor_maximo:
        return False

    return True


def enviar_alerta_telegram(token: str, chat_id: str, edital: dict) -> bool:
    """Envia uma mensagem formatada para o Telegram com os detalhes do edital compatível."""
    if not token or not chat_id:
        return False

    valor_fmt = f"R$ {edital.get('valor_estimado', 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    mensagem = (
        "🔔 *Novo Edital Compatível*\n\n"
        f"*Órgão:* {edital.get('orgao', 'N/A')}\n"
        f"*Objeto:* {edital.get('objeto', 'N/A')}\n"
        f"*Valor Estimado:* {valor_fmt}\n"
        f"*Data da Sessão:* {edital.get('data_sessao', 'N/A')}\n"
        f"*Link:* {edital.get('link', 'N/A')}"
    )

    try:
        resp = requests.post(
            TELEGRAM_API_URL.format(token=token),
            json={"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"},
            timeout=10,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False


def processar_perfil(perfil, session, dias_retroativos: int = 1) -> list[dict]:
    """
    Busca editais no PNCP, aplica o matching para o perfil informado, registra os editais
    inéditos no banco (evitando duplicidade) e dispara alertas no Telegram.

    Retorna a lista de editais que deram match nesta execução (novos ou já registrados).
    """
    from models.models import EditalNotificado

    estados = perfil.lista_estados()
    editais_brutos = []
    if estados:
        for uf in estados:
            editais_brutos.extend(buscar_editais_pncp(dias_retroativos=dias_retroativos, uf=uf))
    else:
        editais_brutos = buscar_editais_pncp(dias_retroativos=dias_retroativos)

    matches = []
    for edital in editais_brutos:
        if not calcular_match(edital, perfil):
            continue

        ja_existe = (
            session.query(EditalNotificado)
            .filter_by(empresa_id=perfil.id, numero_controle_pncp=edital["numero_controle_pncp"])
            .first()
        )

        if ja_existe:
            matches.append(edital)
            continue

        registro = EditalNotificado(
            empresa_id=perfil.id,
            numero_controle_pncp=edital["numero_controle_pncp"],
            orgao=edital["orgao"],
            objeto=edital["objeto"],
            valor_estimado=edital["valor_estimado"],
            data_sessao=edital["data_sessao"],
            link=edital["link"],
        )
        session.add(registro)
        session.commit()

        enviar_alerta_telegram(perfil.telegram_token, perfil.telegram_chat_id, edital)
        matches.append(edital)

    return matches
