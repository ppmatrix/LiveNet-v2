-- F0.66C: validacao obrigatoria da sessao administrativa.
-- Executar exclusivamente no cluster PostgreSQL isolado.
-- A excecao impede a continuacao com ON_ERROR_STOP=1.

DO $f066c_guard$
BEGIN
    IF current_user <> 'livenet'
       OR session_user <> 'livenet'
       OR current_database() <> 'livenet_f0_test'
       OR inet_client_addr() IS NULL
    THEN
        RAISE EXCEPTION
            'F0.66C: identidade administrativa PostgreSQL inesperada'
            USING ERRCODE = '28000';
    END IF;
END
$f066c_guard$;
