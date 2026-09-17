import pathlib

p = pathlib.Path('app.py')
text = p.read_text(encoding='utf-8')

replacements = [
    (
        "login_user(user)\n        return jsonify({'message': 'Login successful', 'mensagem': 'Login bem-sucedido'})",
        "login_user(user)\n        registrar_log('LOGIN_SUCCESS', 'User', user.id, f\"Usuário {user.nome} fez login no sistema.\")\n        return jsonify({'message': 'Login successful', 'mensagem': 'Login bem-sucedido'})"
    ),
    (
        "@app.route('/logout', methods=['GET', 'POST'])\n@login_required\ndef logout():\n    logout_user()",
        "@app.route('/logout', methods=['GET', 'POST'])\n@login_required\ndef logout():\n    operador_atual = current_user.nome if current_user.is_authenticated else 'System'\n    uid = current_user.id if current_user.is_authenticated else None\n    if uid: registrar_log('LOGOUT', 'User', uid, f\"Usuário {operador_atual} fez logout.\")\n    logout_user()"
    ),
    (
        "contrato.url_seguro = f\"/static/uploads/{nome_salvo}\"\n            db.session.commit()\n            return jsonify({'message': 'Insurance document updated successfully', 'mensagem': 'Seguro atualizado'})",
        "contrato.url_seguro = f\"/static/uploads/{nome_salvo}\"\n            db.session.commit()\n            operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'\n            registrar_log('INSURANCE_UPLOADED', 'Contract', contrato.id, f\"Apólice de seguro do contrato #{contrato.id} atualizada por {operador_atual}.\")\n            return jsonify({'message': 'Insurance document updated successfully', 'mensagem': 'Seguro atualizado'})"
    ),
    (
        "db.session.commit()\n    return jsonify({'message': 'Transaction deleted successfully', 'mensagem': 'Transação excluída'})",
        "db.session.commit()\n    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'\n    registrar_log('TRANSACTION_DELETE', 'Transaction', id, f\"Transação #{id} deletada por {operador_atual}.\")\n    return jsonify({'message': 'Transaction deleted successfully', 'mensagem': 'Transação excluída'})"
    ),
    (
        "db.session.commit()\n    \n    return jsonify({'message': 'Quarantine finalized', 'mensagem': 'Quarentena finalizada'})",
        "db.session.commit()\n    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'\n    registrar_log('QUARANTINE_END', 'Contract', contrato.id, f\"Quarentena do contrato #{contrato.id} finalizada manualmente por {operador_atual}.\")\n    return jsonify({'message': 'Quarantine finalized', 'mensagem': 'Quarentena finalizada'})"
    ),
    (
        "db.session.commit()\n    return jsonify({'message': f'{count} charges generated', 'mensagem': f'{count} cobranças geradas'})",
        "db.session.commit()\n    registrar_log('JOB_WEEKLY_RENT', 'System', None, f\"Job de cobranças semanais executado. {count} novas cobranças geradas.\")\n    return jsonify({'message': f'{count} charges generated', 'mensagem': f'{count} cobranças geradas'})"
    ),
    (
        "db.session.commit()\n    return jsonify({'message': f'{count} contracts updated', 'mensagem': f'{count} contratos atualizados'})",
        "db.session.commit()\n    registrar_log('JOB_QUARANTINE', 'System', None, f\"Job de quarentena executado. {count} contratos finalizados automaticamente.\")\n    return jsonify({'message': f'{count} contracts updated', 'mensagem': f'{count} contratos atualizados'})"
    )
]

for find_str, replace_str in replacements:
    if find_str in text:
        text = text.replace(find_str, replace_str)
        print(f"Replaced {find_str[:30]}...")
    else:
        print(f"NOT FOUND: {find_str[:30]}...")

p.write_text(text, encoding='utf-8')
