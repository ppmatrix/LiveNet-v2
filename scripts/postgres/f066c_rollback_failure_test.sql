-- F0.66C: teste controlado de rollback por falha.
-- EXCLUSIVAMENTE para o cluster PostgreSQL isolado.
-- Nao executar diretamente: requer guarda de sessao previa
-- e executor com ON_ERROR_STOP=1.
--
-- A transacao e iniciada pelo executor, antes da guarda.
-- O executor nao deve acrescentar COMMIT apos este ficheiro.

CREATE TABLE inventory.f066c_rollback_probe (
    id integer PRIMARY KEY,
    description text NOT NULL
);

SELECT 'F066C_CREATE_COMPLETED';

INSERT INTO inventory.f066c_rollback_probe (id, description)
VALUES (1, 'F066C_ROLLBACK_TEST');

SELECT 'F066C_INSERT_COMPLETED'
WHERE EXISTS (
    SELECT 1
    FROM inventory.f066c_rollback_probe
    WHERE id = 1
      AND description = 'F066C_ROLLBACK_TEST'
);

DO $f066c_failure$
BEGIN
    RAISE EXCEPTION
        'F0.66C: falha intencional para validar rollback'
        USING ERRCODE = 'P0001';
END
$f066c_failure$;
