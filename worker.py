"""
Worker standalone para monitoramento em background.

Executa a varredura do PNCP para todas as empresas cadastradas e dispara
alertas via Telegram. Pode ser agendado via cron / Task Scheduler para
rodar periodicamente (ex: a cada 1 hora), sem depender da interface Streamlit.

Uso:
    python worker.py
"""
from database.db import init_db, get_session
from models.models import EmpresaPerfil
from services.pncp_service import processar_perfil


def main():
    init_db()
    session = get_session()

    perfis = session.query(EmpresaPerfil).all()
    if not perfis:
        print("Nenhum perfil de empresa cadastrado. Cadastre um perfil pelo app.py antes de rodar o worker.")
        return

    for perfil in perfis:
        print(f"Processando perfil: {perfil.nome_empresa}...")
        matches = processar_perfil(perfil, session, dias_retroativos=1)
        print(f"  -> {len(matches)} edital(is) compatível(is).")

    session.close()


if __name__ == "__main__":
    main()
