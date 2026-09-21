"""Monitor Inteligente e Agregador de Oportunidades do PNCP — Interface Streamlit."""
import pandas as pd
import streamlit as st

from database.db import init_db, get_session
from models.models import EmpresaPerfil, EditalNotificado
from services.pncp_service import processar_perfil

st.set_page_config(page_title="Monitor PNCP", page_icon="📋", layout="wide")

init_db()


def carregar_empresas(session):
    return session.query(EmpresaPerfil).order_by(EmpresaPerfil.nome_empresa).all()


def preencher_perfil_exemplo():
    st.session_state["nome_empresa"] = "TechSolutions Ltda (Exemplo TI)"
    st.session_state["palavras_positivas"] = "desenvolvimento de software, licenças, nuvem, sistema de gestão"
    st.session_state["palavras_negativas"] = "manutenção física, cabeamento, obras civis"
    st.session_state["estados"] = "SP, RJ, MG"
    st.session_state["valor_minimo"] = 10000.0
    st.session_state["valor_maximo"] = 500000.0
    st.session_state["telegram_token"] = ""
    st.session_state["telegram_chat_id"] = ""


st.title("📋 Monitor Inteligente de Oportunidades do PNCP")
st.caption("Cadastre perfis de interesse e receba alertas automáticos de licitações compatíveis.")

tab_cadastro, tab_dashboard = st.tabs(["📝 Cadastro de Perfil", "📊 Dashboard de Oportunidades Filtradas"])

with tab_cadastro:
    st.subheader("Cadastrar novo perfil de interesse")

    st.button("⚡ Carregar Perfil de Exemplo (TI)", on_click=preencher_perfil_exemplo)

    with st.form("form_perfil"):
        nome_empresa = st.text_input("Nome da empresa", key="nome_empresa")
        palavras_positivas = st.text_area(
            "Palavras-chave positivas (separadas por vírgula)",
            key="palavras_positivas",
            placeholder="ex: desenvolvimento de software, licenças, nuvem",
        )
        palavras_negativas = st.text_area(
            "Palavras-chave negativas / exclusão (separadas por vírgula)",
            key="palavras_negativas",
            placeholder="ex: manutenção física, cabeamento",
        )
        estados = st.text_input(
            "Filtro por Estado - UFs (separadas por vírgula, vazio = todas)",
            key="estados",
            placeholder="ex: SP, RJ, MG",
        )

        col1, col2 = st.columns(2)
        with col1:
            valor_minimo = st.number_input("Valor mínimo estimado (R$)", min_value=0.0, step=1000.0, key="valor_minimo")
        with col2:
            valor_maximo = st.number_input("Valor máximo estimado (R$)", min_value=0.0, step=1000.0, key="valor_maximo")

        st.markdown("**Destino do Alerta (Telegram)**")
        col3, col4 = st.columns(2)
        with col3:
            telegram_token = st.text_input("Token do Bot", key="telegram_token", type="password")
        with col4:
            telegram_chat_id = st.text_input("Chat ID", key="telegram_chat_id")

        submitted = st.form_submit_button("💾 Salvar Perfil")

        if submitted:
            if not nome_empresa or not palavras_positivas:
                st.error("Preencha ao menos o nome da empresa e as palavras-chave positivas.")
            else:
                session = get_session()
                perfil = EmpresaPerfil(
                    nome_empresa=nome_empresa,
                    palavras_chave_positivas=palavras_positivas,
                    palavras_chave_negativas=palavras_negativas,
                    estados=estados,
                    valor_minimo=valor_minimo,
                    valor_maximo=valor_maximo,
                    telegram_token=telegram_token,
                    telegram_chat_id=telegram_chat_id,
                )
                session.add(perfil)
                session.commit()
                session.close()
                st.success(f"Perfil '{nome_empresa}' salvo com sucesso!")

with tab_dashboard:
    st.subheader("Dashboard de Oportunidades Filtradas")

    session = get_session()
    empresas = carregar_empresas(session)

    if not empresas:
        st.info("Nenhuma empresa cadastrada ainda. Vá até a aba 'Cadastro de Perfil'.")
    else:
        nomes = {e.nome_empresa: e.id for e in empresas}
        empresa_selecionada = st.selectbox("Selecione a empresa", list(nomes.keys()))
        perfil = session.query(EmpresaPerfil).get(nomes[empresa_selecionada])

        col_a, col_b = st.columns([1, 3])
        with col_a:
            if st.button("🔍 Buscar Editais Agora"):
                with st.spinner("Consultando API do PNCP e aplicando filtros..."):
                    matches = processar_perfil(perfil, session, dias_retroativos=3)
                st.success(f"{len(matches)} edital(is) compatível(is) encontrado(s) nesta busca.")

        registros = (
            session.query(EditalNotificado)
            .filter_by(empresa_id=perfil.id)
            .order_by(EditalNotificado.notificado_em.desc())
            .all()
        )

        if not registros:
            st.info("Nenhum edital compatível registrado ainda para esta empresa. Clique em 'Buscar Editais Agora'.")
        else:
            df = pd.DataFrame(
                [
                    {
                        "Órgão": r.orgao,
                        "Objeto": r.objeto,
                        "Valor Estimado": r.valor_estimado,
                        "Data da Sessão": r.data_sessao,
                        "Link": r.link,
                        "Notificado em": r.notificado_em,
                    }
                    for r in registros
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("### Cards de Oportunidades")
            for r in registros:
                with st.container(border=True):
                    st.markdown(f"**{r.orgao}**")
                    st.write(r.objeto)
                    col_x, col_y, col_z = st.columns(3)
                    col_x.metric("Valor Estimado", f"R$ {r.valor_estimado:,.2f}")
                    col_y.write(f"📅 {r.data_sessao}")
                    col_z.markdown(f"[🔗 Ver no PNCP]({r.link})")

    session.close()
