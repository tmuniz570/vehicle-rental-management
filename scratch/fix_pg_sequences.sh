#!/bin/bash
sudo -u postgres psql -d ffmotors_db <<EOF
DO \$\$
DECLARE
    t_name text;
    seq_name text;
    max_id bigint;
BEGIN
    FOR t_name IN 
        SELECT unnest(ARRAY['usuarios', 'clientes', 'contratos', 'contrato_anexos', 'vistorias', 'financeiro_transacoes', 'logs_auditoria', 'claims', 'job_locks'])
    LOOP
        seq_name := t_name || '_id_seq';
        
        -- Create sequence
        EXECUTE 'CREATE SEQUENCE IF NOT EXISTS ' || seq_name;
        
        -- Get max id
        EXECUTE 'SELECT COALESCE(MAX(id), 0) + 1 FROM ' || t_name INTO max_id;
        
        -- Set sequence value
        EXECUTE 'SELECT setval(''' || seq_name || ''', ' || max_id || ')';
        
        -- Alter table to use sequence
        EXECUTE 'ALTER TABLE ' || t_name || ' ALTER COLUMN id SET DEFAULT nextval(''' || seq_name || ''')';
        
        -- Give permissions
        EXECUTE 'GRANT ALL ON SEQUENCE ' || seq_name || ' TO ffmotors_user';
    END LOOP;
END \$\$;
EOF
