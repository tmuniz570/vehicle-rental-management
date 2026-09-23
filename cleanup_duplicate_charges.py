#!/usr/bin/env python3
"""
cleanup_duplicate_charges.py
============================
Script utilitário para auditar e limpar com segurança cobranças de aluguel semanais
duplicadas geradas em produção por concorrência de workers.

Regras de Segurança:
1. Afeta APENAS transações do tipo 'Rent'/'Aluguel' com status 'PENDING'/'Pendente'.
2. NUNCA toca em depósitos, multas, vendas ou transações já PAGAS.
3. Para cada grupo de cobranças do mesmo contrato na mesma data de vencimento,
   preserva SEMPRE a transação original (menor ID) e remove apenas as excedentes.

Uso:
  python cleanup_duplicate_charges.py           # Modo simulação (dry-run, não altera o banco)
  python cleanup_duplicate_charges.py --apply   # Aplica a limpeza definitiva com confirmação
  python cleanup_duplicate_charges.py --apply -y # Aplica a limpeza sem confirmação interativa
"""

import sys
import argparse
from app import app, db, _limpar_cobrancas_semanais_duplicadas_logic
from database import Contract, Motorcycle, Client

def main():
    parser = argparse.ArgumentParser(description="Limpeza segura de cobranças semanais pendentes duplicadas.")
    parser.add_argument("--apply", action="store_true", help="Executa a deleção das cobranças duplicadas do banco.")
    parser.add_argument("-y", "--yes", action="store_true", help="Confirma automaticamente a exclusão.")
    args = parser.parse_args()

    is_dry_run = not args.apply

    print("\n" + "=" * 70)
    print("  FF MOTORS - AUDITORIA E LIMPEZA DE COBRANÇAS DUPLICADAS")
    print("=" * 70)
    print(f"Modo de Operação: {'[SIMULAÇÃO / DRY-RUN] (Nenhum dado será alterado)' if is_dry_run else '[APLICAÇÃO REAL] (Registros duplicados serão deletados)'}\n")

    with app.app_context():
        res = _limpar_cobrancas_semanais_duplicadas_logic(dry_run=True)
        total = res["total_duplicadas"]
        detalhes = res["detalhes"]

        if total == 0:
            print("✓ Nenhuma cobrança duplicada encontrada no banco de dados!")
            print("  O sistema financeiro está 100% íntegro.\n")
            return 0

        print(f"(!) Foram identificadas {total} cobrança(s) pendente(s) duplicada(s):\n")
        print(f"{'Contrato':<10} | {'Cliente':<25} | {'Placa':<10} | {'Vencimento':<12} | {'Valor':<8} | {'Manter ID':<10} | {'Remover ID'}")
        print("-" * 105)

        for d in detalhes:
            contrato = db.session.get(Contract, d["id_contrato"])
            cliente_nome = "Desconhecido"
            placa = "-"
            if contrato:
                placa = contrato.placa or "-"
                cliente = db.session.get(Client, contrato.id_cliente) if contrato.id_cliente else None
                if cliente:
                    cliente_nome = cliente.nome[:24]

            print(f"#{d['id_contrato']:<9} | {cliente_nome:<25} | {placa:<10} | {d['vencimento']:<12} | £{d['valor']:<7.2f} | #{d['id_mantido']:<9} | #{d['id_removido']}")

        print("-" * 105)

        if is_dry_run:
            print(f"\n[DRY-RUN] Simulação concluída. {total} cobranças duplicadas seriam removidas.")
            print("Para aplicar as alterações e deletar os registros duplicados no banco de dados, execute:")
            print("  python cleanup_duplicate_charges.py --apply\n")
            return 0

        if not args.yes:
            confirm = input(f"\nTem certeza de que deseja deletar permanentemente as {total} cobranças duplicadas listadas acima? (s/N): ")
            if confirm.strip().lower() not in ('s', 'sim', 'y', 'yes'):
                print("Operação cancelada pelo usuário. Nenhuma alteração foi feita no banco.\n")
                return 0

        print("\nExecutando limpeza no banco de dados...")
        exec_res = _limpar_cobrancas_semanais_duplicadas_logic(dry_run=False)
        print(f"✓ SUCESSO: {exec_res['total_duplicadas']} cobranças duplicadas foram removidas permanentemente do banco de dados!")
        print("  As cobranças originais foram devidamente mantidas.\n")
        return 0

if __name__ == '__main__':
    sys.exit(main())
