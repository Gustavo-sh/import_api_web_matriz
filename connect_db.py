import pyodbc
from utils import notify

CONNECTION_STRING = "Driver={SQL Server};Server=primno4;Database=Robbyson;Trusted_Connection=yes;"

gerador_importacao = """
use robbysonmatriz
------------------------------------------------------------            GERADOR            -------------------------------------------------------------------------------

if object_id('tempdb..#importations') is not null drop table #importations
if object_id('tempdb..#first_importation') is not null drop table #first_importation
if object_id('tempdb..#alterations') is not null drop table #alterations

; WITH base AS (
    SELECT
        id_indicador,
        data_inicio,
        data_fim,
        periodo,
        meta_final as meta,
        atributo,
        moedas,
        acumulado,
        escala,
        case when dmm is null then '' else dmm end as dmm,
        tipo_matriz,
        esquema_acumulado,
        ativo,
        CASE 
            WHEN TRY_CONVERT(TIME, meta) IS NOT NULL 
                THEN DATEDIFF(SECOND, 0, TRY_CONVERT(TIME, meta)) / 60.0
            WHEN ISNUMERIC(meta) = 1 
                THEN TRY_CAST(meta AS DECIMAL(18,2))
            ELSE NULL
        END AS meta_num
    FROM robbysonmatriz.dbo.sistema_matriz (nolock)
    WHERE
    importado = 0
    and importacao_valida = 1
    and matriz_coletada = 0
    and ativo in (0, 1, 3)
    and periodo = dateadd(d, 1, eomonth(getdate(), -1))
    and (atributo in (select distinct atributo from robbysonmatriz.dbo.publico_piloto_sistema_matriz (nolock)))
    and moedas <= 35
),

-- OS INDICADORES DA CTR_FIXOS ABAIXO DEVEM SER COLOCADOS APENAS NAS MATRIZES ONDE O TIPO_MATRIZ = OPERAÇÃO
CTE_Fixos AS (
    SELECT * FROM (VALUES
        ('4',         '00:00:00',   0.0,   0.0,   0.0,   0.0),
        ('48',           '2.0',   0.0,   0.0,   0.0,   0.0), 
        ('49',           '2.0',   0.0,   0.0,   0.0, -90.0),
        ('51',     '00:00:00',   0.0,   0.0,   0.0,   0.0),
        ('52',  '00:00:00',   0.0,   0.0,   0.0,   0.0),
        ('53',     '00:00:00',   0.0,   0.0,   0.0,   0.0),
        ('54',      '00:00:00',   0.0,   0.0,   0.0,   0.0),
        ('55',       '00:00:00',   0.0,   0.0,   0.0,   0.0),
        ('56',   '00:00:00',   0.0,   0.0,   0.0,   0.0),
        ('57',        '00:00:00',   0.0,   0.0,   0.0,   0.0),
        ('58',      '00:00:00',   0.0,   0.0,   0.0,   0.0),
        ('59',      '00:00:00',   0.0,   0.0,   0.0,   0.0),
        ('467', '00:00:00',   0.0,   0.0,   0.0,   0.0),
        ('522',      '00:00:00',   0.0,   0.0,   0.0,   0.0),
        ('742',       '00:00:00',   0.0,   0.0,   0.0,   0.0),
        ('772', '90.0',   0.0,   0.0,   0.0,   0.0), 
        ('773', '80.0', 0.0, 0.0, 0.0, 0.0), 
        ('25', '00:00:00', 0.0, 0.0, 0.0, 0.0),
        ('6', '0.0', 0.0, 0.0, 0.0, 0.0),
        ('15', '00:00:00', 0.0, 0.0, 0.0, 0.0)
    ) AS t(id_indicador, meta_def, ganho_g1_def, ganho_g2_def, ganho_g3_def, ganho_g4_def)
),

-- INDICADORES QUE DEFLACIONAM E QUANTO DEFLACIONAM
CTE_Fixos_Especiais AS (
    SELECT
        'OPERACIONAL' AS tipo_matriz,
        atributo,
        id_indicador AS indicador,
        meta,
        ganho_g1     AS meta2,
        ganho_g2     AS meta3,
        ganho_g3     AS meta4,
        ganho_g4     AS meta5
    FROM dbo.deflatores_sistema_matriz (nolock)

    UNION ALL

    SELECT 
        m.tipo_matriz, 
        m.atributo, 
        249 AS indicador, 
        '0' AS meta, 
        0   AS meta2, 
        0   AS meta3, 
        -90 AS meta4, 
        -90 AS meta5
    FROM base m
    WHERE m.tipo_matriz IN ('OPERAÇÃO', 'OPERACIONAL')
      AND m.atributo LIKE '%PETROBRAS SAUDE%'
      AND m.ativo IN (0, 1, 3)

    UNION ALL

    SELECT 
        m.tipo_matriz, 
        m.atributo, 
        341  AS indicador, 
        '90' AS meta, 
        0    AS meta2, 
        0    AS meta3, 
        0    AS meta4, 
        0    AS meta5
    FROM base m
    WHERE m.tipo_matriz = 'OPERACIONAL'
      AND m.ativo IN (0, 1, 3)

    UNION ALL

    SELECT DISTINCT
        b.tipo_matriz,
        b.atributo,
        277 AS id_indicador,
        '0' AS meta,
        0   AS ganho_g1,
        CASE 
            WHEN b.atributo LIKE '%SANTANDER CARTOES%' THEN -200
            ELSE 0
        END AS ganho_g2,
        CASE 
            WHEN b.atributo LIKE '%SANTANDER CARTOES%' THEN -200
            ELSE 0
        END AS ganho_g3,
        CASE 
            WHEN b.atributo LIKE '%SANTANDER CARTOES%' THEN -200
            ELSE 0
        END AS ganho_g4
    FROM base b
    WHERE b.atributo LIKE '%SANTANDER%'
    AND b.atributo NOT IN (SELECT atributo FROM dbo.deflatores_sistema_matriz (nolock) WHERE id_indicador = 277)
),

base_fixos AS (
    SELECT b.*, f.meta_def, f.ganho_g1_def, f.ganho_g2_def, f.ganho_g3_def, f.ganho_g4_def
    FROM base b
    INNER JOIN CTE_Fixos f
      ON b.id_indicador = f.id_indicador
),

base_nonfixos AS (
    SELECT b.*
    FROM base b
    LEFT JOIN CTE_Fixos f ON b.id_indicador = f.id_indicador
    where b.id_indicador not in (48)
),

/* NAO-ACUMULADOS */
CTE_NA_Datas AS (
    SELECT 
        b.id_indicador, b.data_inicio, b.data_fim, b.meta, b.meta_num, b.atributo, b.moedas, b.acumulado, b.escala, b.dmm,
        CAST(b.data_inicio AS date) AS data_dia, b.ativo
    FROM base_nonfixos b
    WHERE b.acumulado = 'NAO'
    AND b.esquema_acumulado <> 'MENSAL' -- ADICIONADO APOS OS MENSAIS TEREM SUA PROPRIA CTE
    AND b.moedas <> 0

    UNION ALL

    SELECT 
        d.id_indicador, d.data_inicio, d.data_fim, d.meta, d.meta_num, d.atributo, d.moedas, d.acumulado, d.escala, d.dmm,
        DATEADD(DAY, 1, d.data_dia), d.ativo
    FROM CTE_NA_Datas d
    WHERE d.data_dia < d.data_fim
),

CTE_NA_Marcado AS (
    SELECT
        id_indicador, data_inicio, data_fim, meta, meta_num, atributo, moedas, acumulado, escala, dmm, data_dia,
        CASE 
            WHEN dmm IS NULL OR LTRIM(RTRIM(dmm)) = '' THEN 0 -- Sem DMM declarado
            WHEN CHARINDEX(CONVERT(varchar(10), data_dia, 23), REPLACE(REPLACE(dmm, ' ', ''), ',', ',')) > 0 THEN 3
            ELSE 1
        END AS multiplicador, ativo
    FROM CTE_NA_Datas
),

CTE_NA_Quebra AS (
    SELECT *,
        CASE WHEN LAG(multiplicador) OVER (
    PARTITION BY 
        id_indicador,
        atributo,
        data_inicio,
        data_fim,
        meta
    ORDER BY data_dia
) <> multiplicador
              OR LAG(multiplicador) OVER (
    PARTITION BY 
        id_indicador,
        atributo,
        data_inicio,
        data_fim,
        meta
    ORDER BY data_dia
) IS NULL
             THEN 1 ELSE 0 END AS nova_faixa
    FROM CTE_NA_Marcado
),

CTE_NA_Grupos AS (
    SELECT *,
        SUM(nova_faixa) OVER (
            PARTITION BY id_indicador, atributo, data_inicio, data_fim, meta
            ORDER BY data_dia ROWS UNBOUNDED PRECEDING
        ) AS grupo
    FROM CTE_NA_Quebra
),

CTE_Final_NAcum AS (
    SELECT
        id_indicador,
        atributo,
        MIN(data_dia) AS data_inicio,
        MAX(data_dia) AS data_fim,
        CAST(MAX(meta) AS VARCHAR(20)) AS meta,
        CAST(MAX(meta_num) AS DECIMAL(18,2)) AS meta_num,
        max(ativo) AS ativo,
        CASE WHEN multiplicador = 3 THEN moedas * 3 ELSE moedas END AS ganho_g1,
        ROUND(CASE WHEN multiplicador = 3 THEN moedas * 3 ELSE moedas END * 0.7, 2) AS ganho_g2,
        ROUND(CASE WHEN multiplicador = 3 THEN moedas * 3 ELSE moedas END * 0.1, 2) AS ganho_g3,
        0 AS ganho_g4
    FROM CTE_NA_Grupos
    GROUP BY id_indicador, atributo, meta, meta_num, multiplicador, moedas, grupo, data_inicio, data_fim
),

/* ACUMULADOS (pagamento sempre no 7º dia; peso muda por escala) */
CTE_Acumulado_Diario AS (
    SELECT 
        b.id_indicador, b.data_inicio, b.data_fim, b.meta, b.meta_num, b.atributo, b.moedas, b.acumulado, b.escala,
        CAST(b.data_inicio AS date) AS data_dia, b.ativo
    FROM base_nonfixos b
    WHERE b.acumulado = 'SIM'
    AND b.moedas <> 0

    UNION ALL

    SELECT 
        a.id_indicador, a.data_inicio, a.data_fim, a.meta, a.meta_num, a.atributo, a.moedas, a.acumulado, a.escala,
        DATEADD(DAY, 1, a.data_dia), a.ativo
    FROM CTE_Acumulado_Diario a
    WHERE a.data_dia < a.data_fim
),

CTE_Acumulado_Com_Sequencia AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY id_indicador, atributo ORDER BY data_dia) AS rn
    FROM CTE_Acumulado_Diario
),

CTE_Acumulado_Blocos AS ( 
    SELECT
        id_indicador, data_inicio, data_fim, meta, meta_num, atributo, acumulado, escala, moedas, data_dia, rn,
        ((rn - 1) / 7) AS bloco, ativo
    FROM CTE_Acumulado_Com_Sequencia
),

CTE_Block_Stats AS (
    SELECT
        id_indicador,
        atributo,
        bloco,
        MIN(data_dia) AS bloco_start,
        MAX(data_dia) AS bloco_end,
        COUNT(*) AS dias_no_bloco,
        MAX(moedas) AS moedas,
        MAX(escala) AS escala,
        CAST(MAX(meta) AS VARCHAR(20)) AS meta,
        MAX(meta_num) AS meta_num,
        MAX(ativo) AS ativo
    FROM CTE_Acumulado_Blocos
    GROUP BY id_indicador, atributo, bloco
),

CTE_Final_Acum AS (

    -- blocos completos (7 dias): dias 1..6 -> ganho 0  (válido para 6X1 e 5X2)
    SELECT
        bs.id_indicador,
        bs.atributo,
        bs.bloco_start AS data_inicio,
        DATEADD(DAY, 5, bs.bloco_start) AS data_fim,
        bs.meta,
        bs.meta_num,
        bs.ativo,
        0.0 AS ganho_g1, 0.0 AS ganho_g2, 0.0 AS ganho_g3, 0 AS ganho_g4
    FROM CTE_Block_Stats bs
    WHERE bs.dias_no_bloco = 7
      AND bs.escala IN ('6X1','5X2')

    UNION ALL

    -- blocos completos (7 dias): dia 7 -> pagamento com peso (6 para 6X1, 5 para 5X2)
    SELECT
        bs.id_indicador,
        bs.atributo,
        DATEADD(DAY, 6, bs.bloco_start) AS data_inicio,
        DATEADD(DAY, 6, bs.bloco_start) AS data_fim,
        bs.meta,
        bs.meta_num,
        bs.ativo,
        CAST(
          CASE WHEN bs.escala = '6X1' THEN bs.moedas * 6
               WHEN bs.escala = '5X2' THEN bs.moedas * 5
               ELSE bs.moedas
          END AS DECIMAL(18,2)
        ) AS ganho_g1,
        ROUND(
          CAST(
            CASE WHEN bs.escala = '6X1' THEN bs.moedas * 6
                 WHEN bs.escala = '5X2' THEN bs.moedas * 5
                 ELSE bs.moedas
            END AS DECIMAL(18,2)
          ) * 0.7, 2
        ) AS ganho_g2,
        ROUND(
          CAST(
            CASE WHEN bs.escala = '6X1' THEN bs.moedas * 6
                 WHEN bs.escala = '5X2' THEN bs.moedas * 5
                 ELSE bs.moedas
            END AS DECIMAL(18,2)
          ) * 0.1, 2
        ) AS ganho_g3,
        0 AS ganho_g4
    FROM CTE_Block_Stats bs
    WHERE bs.dias_no_bloco = 7
      AND bs.escala IN ('6X1','5X2')

    UNION ALL

    -- Blocos parciais (último bloco): pagamento proporcional = moedas * dias_no_bloco (ambas escalas)
    SELECT
        bs.id_indicador,
        bs.atributo,
        bs.bloco_start AS data_inicio,
        bs.bloco_end AS data_fim,
        bs.meta,
        bs.meta_num,
        bs.ativo,
        CAST(bs.moedas * bs.dias_no_bloco AS DECIMAL(18,2)) AS ganho_g1,
        ROUND(CAST(bs.moedas * bs.dias_no_bloco AS DECIMAL(18,2)) * 0.7, 2) AS ganho_g2,
        ROUND(CAST(bs.moedas * bs.dias_no_bloco AS DECIMAL(18,2)) * 0.1, 2) AS ganho_g3,
        0 AS ganho_g4
    FROM CTE_Block_Stats bs
    WHERE bs.dias_no_bloco < 7
),

CTE_Acumulado_Mensal AS (
    SELECT 
        b.id_indicador,
        b.atributo,
        DATEFROMPARTS(YEAR(b.data_inicio), MONTH(b.data_inicio), 1) AS data_inicio,
        DATEADD(DAY, -1, EOMONTH(b.data_inicio)) AS data_fim,
        b.meta,
        b.meta_num,
        b.ativo,
        0.0 AS ganho_g1, 0.0 AS ganho_g2, 0.0 AS ganho_g3, 0 AS ganho_g4
    FROM base_nonfixos b
    WHERE b.acumulado = 'NAO'
      AND b.esquema_acumulado = 'MENSAL'
      AND b.moedas <> 0

    UNION ALL

    SELECT 
        b.id_indicador,
        b.atributo,
        EOMONTH(b.data_inicio) AS data_inicio,
        EOMONTH(b.data_inicio) AS data_fim,
        b.meta,
        b.meta_num,
        b.ativo,
        CASE 
            WHEN b.escala = '6X1' THEN b.moedas * 
                (SELECT COUNT(*) FROM master..spt_values 
                 WHERE type='P' 
                 AND DATEPART(WEEKDAY, DATEADD(DAY, number, DATEFROMPARTS(YEAR(b.data_inicio), MONTH(b.data_inicio), 1))) BETWEEN 2 AND 7
                 AND DATEADD(DAY, number, DATEFROMPARTS(YEAR(b.data_inicio), MONTH(b.data_inicio), 1)) <= EOMONTH(b.data_inicio))
            WHEN b.escala = '5X2' THEN b.moedas * 
                (SELECT COUNT(*) FROM master..spt_values 
                 WHERE type='P' 
                 AND DATEPART(WEEKDAY, DATEADD(DAY, number, DATEFROMPARTS(YEAR(b.data_inicio), MONTH(b.data_inicio), 1))) BETWEEN 2 AND 6
                 AND DATEADD(DAY, number, DATEFROMPARTS(YEAR(b.data_inicio), MONTH(b.data_inicio), 1)) <= EOMONTH(b.data_inicio))
            ELSE b.moedas
        END AS ganho_g1,
        ROUND(
            CASE 
                WHEN b.escala = '6X1' THEN b.moedas * 6 * 0.7
                WHEN b.escala = '5X2' THEN b.moedas * 5 * 0.7
                ELSE b.moedas * 0.7
            END, 2
        ) AS ganho_g2,
        ROUND(
            CASE 
                WHEN b.escala = '6X1' THEN b.moedas * 6 * 0.1
                WHEN b.escala = '5X2' THEN b.moedas * 5 * 0.1
                ELSE b.moedas * 0.1
            END, 2
        ) AS ganho_g3,
        0 AS ganho_g4
    FROM base_nonfixos b
    WHERE b.acumulado = 'NAO'
      AND b.esquema_acumulado = 'MENSAL'
      AND b.moedas <> 0

    union all

    SELECT
        b.id_indicador,
        b.atributo,
        b.data_inicio,
        b.data_fim,
        b.meta,
        b.meta_num,
        b.ativo,
        0.0 AS ganho_g1,
        0.0 AS ganho_g2,
        0.0 AS ganho_g3,
        0 AS ganho_g4
    FROM base_nonfixos b
    WHERE b.acumulado = 'NAO'
      AND b.esquema_acumulado = 'MENSAL'
      AND b.moedas = 0
),

/* Preservar fixos que já existem na robbyson.dbo.sistema_matriz */
CTE_Final_Base_Fixos AS (
    SELECT
        b.id_indicador,
        b.atributo,
        b.data_inicio,
        b.data_fim,
        COALESCE(b.meta, CAST(f.meta_def AS VARCHAR(20))) AS meta,
        b.ativo,
        CASE 
            WHEN b.moedas IS NOT NULL AND b.moedas <> 0 
                THEN CAST(b.moedas AS DECIMAL(18,2))
            ELSE f.ganho_g1_def 
        END AS ganho_g1,
        CASE 
            WHEN b.id_indicador = 48 THEN 0
            WHEN b.moedas IS NOT NULL AND b.moedas <> 0 
                THEN ROUND(b.moedas * 0.7, 2)
            ELSE COALESCE(f.ganho_g2_def, ROUND(f.ganho_g1_def * 0.7, 2))
        END AS ganho_g2,
        CASE 
            WHEN b.id_indicador = 48 THEN 0
            WHEN b.moedas IS NOT NULL AND b.moedas <> 0 
                THEN ROUND(b.moedas * 0.1, 2)
            ELSE COALESCE(f.ganho_g3_def, ROUND(f.ganho_g1_def * 0.1, 2))
        END AS ganho_g3,
        CASE 
            WHEN b.id_indicador = 48 THEN 0
            ELSE COALESCE(f.ganho_g4_def, 0)
        END AS ganho_g4
    FROM base_fixos b
    LEFT JOIN CTE_Fixos f ON b.id_indicador = f.id_indicador
    WHERE NOT EXISTS (
        SELECT 1 
        FROM robbysonmatriz.dbo.sistema_matriz (NOLOCK) mg 
        WHERE mg.id_indicador = b.id_indicador
          AND mg.atributo = b.atributo
          AND mg.data_inicio = b.data_inicio
    )
),

CTE_Atributo_Periodo AS (
    SELECT
        atributo,
        periodo,
        ativo,
        MIN(data_inicio) AS attr_start,
        MAX(data_fim)    AS attr_end
    FROM base
    GROUP BY atributo, periodo, ativo
),

CTE_Nao_Monetizados AS (
    SELECT 
        id_indicador,
        atributo,
        data_inicio,
        data_fim,
        CAST(meta AS VARCHAR(20)) AS meta,
        ativo,
        0 AS ganho_g1,
        0 AS ganho_g2,
        0 AS ganho_g3,
        0 AS ganho_g4
    FROM base
    WHERE moedas = 0
),

CTE_Final_Union AS (
    SELECT id_indicador, atributo, data_inicio, data_fim, meta, ativo, ganho_g1, ganho_g2, ganho_g3, ganho_g4 FROM CTE_Final_NAcum
    UNION ALL
    SELECT id_indicador, atributo, data_inicio, data_fim, meta, ativo, ganho_g1, ganho_g2, ganho_g3, ganho_g4 FROM CTE_Final_Acum
    UNION ALL
    SELECT id_indicador, atributo, data_inicio, data_fim, meta, ativo, ganho_g1, ganho_g2, ganho_g3, ganho_g4 FROM CTE_Final_Base_Fixos
    UNION ALL
    SELECT id_indicador, atributo, data_inicio, data_fim, meta, ativo, ganho_g1, ganho_g2, ganho_g3, ganho_g4 FROM CTE_Acumulado_Mensal
    UNION ALL
    SELECT id_indicador, atributo, data_inicio, data_fim, meta, ativo, ganho_g1, ganho_g2, ganho_g3, ganho_g4 FROM CTE_Nao_Monetizados
),

CTE_Fixos_Aplicados AS (
    SELECT 
        a.atributo,
        f.id_indicador,
        f.meta_def,
        f.ganho_g1_def,
        f.ganho_g2_def,
        f.ganho_g3_def,
        f.ganho_g4_def
    FROM (
        SELECT DISTINCT atributo, tipo_matriz
        FROM base
        WHERE ativo IN (0,1,3)
    ) a
    CROSS JOIN CTE_Fixos f
    -- somente gerar combos para matrizes do tipo "OPERAÇÃO"
    WHERE UPPER(a.tipo_matriz) LIKE 'OPERA%'
      -- exclui 772/773 para atributos (MASTER / CNH / CEMIG SAUDE / DIA GROUP BH)
      AND NOT (
           f.id_indicador IN (772, 773)
           AND (
               a.atributo LIKE '%MASTER%'
            OR a.atributo LIKE '%CNH%'
            OR a.atributo LIKE '%CEMIG SAUDE%'
            OR a.atributo LIKE '%DIA GROUP BH%'
            OR a.atributo LIKE '%SANTANDER%'
           )
       ) 
       AND NOT (
           f.id_indicador IN (742)
           AND (
           a.atributo LIKE '%SANTANDER%'
           )
       )
),

CTE_Indicadores_Existentes AS (
    SELECT DISTINCT
        atributo,
        id_indicador,
        data_inicio,
        data_fim
    FROM base
),

CTE_Faltantes AS (
    SELECT
        c.id_indicador,
        c.atributo,
        ap.attr_start AS data_inicio,
        ap.attr_end   AS data_fim,
        CAST(c.meta_def AS VARCHAR(20)) AS meta,
        ap.ativo,
        c.ganho_g1_def AS ganho_g1,
        c.ganho_g2_def AS ganho_g2,
        c.ganho_g3_def AS ganho_g3,
        c.ganho_g4_def AS ganho_g4
    FROM CTE_Fixos_Aplicados c
    LEFT JOIN CTE_Final_Union fu
      ON fu.id_indicador = c.id_indicador
     AND fu.atributo = c.atributo
    LEFT JOIN CTE_Atributo_Periodo ap ON ap.atributo = c.atributo
    LEFT JOIN CTE_Indicadores_Existentes ie
    ON ie.id_indicador = c.id_indicador
    AND ie.atributo = c.atributo
    AND ie.data_inicio = ap.attr_start
    AND ie.data_fim    = ap.attr_end
    WHERE fu.id_indicador IS NULL
      AND ie.id_indicador IS NULL  -- NAO sobrescreve o que já existe na robbyson.dbo.sistema_matriz
),

CTE_Fixos_Especiais_Aplicados AS (
    SELECT distinct
        f.indicador AS id_indicador,
        ap.atributo,
        ap.attr_start AS data_inicio,
        ap.attr_end   AS data_fim,
        CAST(f.meta AS VARCHAR(20)) AS meta,
        ap.ativo,
        f.meta2 AS ganho_g1,
        f.meta3 AS ganho_g2,
        f.meta4 AS ganho_g3,
        f.meta5 AS ganho_g4
    FROM CTE_Atributo_Periodo ap
    JOIN CTE_Fixos_Especiais f
      ON f.atributo = ap.atributo
    where not exists (
        select 1 from base b
        where b.id_indicador = f.indicador
          and b.atributo = ap.atributo
          and b.data_inicio = ap.attr_start
          and b.data_fim = ap.attr_end
    )
), 

-- CTE QUE PERMITE O AJUSTE DE COMPORTAMENTO DA DEFLAÇÃO PARA QUEM FICA G4 EM QUALQUER INDICADOR/ATRIBUTO
CTE_Ajuste_GanhoG4 AS (
    SELECT 
        fu.id_indicador,
        fu.id_indicador AS id,
        fu.data_inicio,
        fu.data_fim,
        fu.meta,
        fu.atributo,
        fu.ativo,
        fu.ganho_g1,
        fu.ganho_g2,
        fu.ganho_g3,
        CASE 
            WHEN fu.id_indicador = 369
                 AND fu.atributo = 'PREMIUM - BRB BKO - BRB_BKO - JP2'
                 AND fu.ganho_g1 > 0
            THEN -10
            ELSE fu.ganho_g4
        END AS ganho_g4
    FROM (
        SELECT * FROM CTE_Final_Union
        UNION ALL
        SELECT * FROM CTE_Faltantes where ativo is not null
        UNION ALL
        SELECT * FROM CTE_Fixos_Especiais_Aplicados
    ) fu
)

SELECT distinct 
        id as id_indicador,
        CONVERT(VARCHAR(10), data_inicio, 103) as data_inicio,
        CONVERT(VARCHAR(10), data_fim, 103) as data_fim,
        meta,
        atributo,
        ativo,
        CAST(ROUND(ganho_g1, 0) AS INT) AS ganho_g1,
        CAST(ROUND(ganho_g2, 0) AS INT) AS ganho_g2,
        CAST(CEILING(ganho_g3)  AS INT) AS ganho_g3,
        CAST(ROUND(ganho_g4, 0) AS INT) AS ganho_g4
into #importations
FROM CTE_Ajuste_GanhoG4
ORDER BY atributo, id, data_inicio, data_fim
OPTION (MAXRECURSION 0);

select distinct id_indicador, data_inicio, data_fim, meta, atributo, 1 as ativo, ganho_g1, ganho_g2, ganho_g3, ganho_g4 
into #first_importation
from #importations 
where (ativo in (0,1))

insert into robbysonmatriz.dbo.gerador_sistema_matriz
select distinct *, getdate() as datetime_exec, 'importacao' as tipo_importacao from #first_importation
"""

select_importacao = """
select distinct * from #first_importation
order by 5 desc
"""

gerador_alteracao = """
select distinct id_indicador, data_inicio, data_fim, meta, atributo, 1 as ativo, ganho_g1, ganho_g2, ganho_g3, ganho_g4
into #alterations 
from #importations 
where ativo in (3)

insert into robbysonmatriz.dbo.gerador_sistema_matriz
select distinct *, getdate() as datetime_exec, 'alteracao' as tipo_importacao from #alterations
"""

select_alteracao = """
select distinct * from #alterations
order by 5 desc
"""

gerador_drops = """
drop table #importations
drop table #first_importation
drop table #alterations
"""

gerador_update_coletado = """
update robbysonmatriz.dbo.sistema_matriz
set
    matriz_coletada = 1
where 
    importado = 0
    and importacao_valida = 1
    and matriz_coletada = 0
    and periodo = dateadd(d, 1, eomonth(getdate(), -1))
    and ativo in (0, 1, 3)
    and atributo in (select distinct atributo from robbysonmatriz.dbo.publico_piloto_sistema_matriz (nolock))
"""

def exec_generator():
    importacoes = []
    alteracoes = []
    cur = None
    with pyodbc.connect(CONNECTION_STRING) as CONN:
        try:
            cur = CONN.cursor()
            cur.execute(gerador_importacao)
            cur.execute(select_importacao)
            importacoes = [
                {
                    "ID_META": "",
                    "INDICADOR": r[0],
                    "DATA_INICIO": r[1],
                    "DATA_FIM": r[2],
                    "VALOR_META": r[3],
                    "ATRIBUTOS": r[4],
                    "ATIVO": r[5],
                    "GANHO_1": r[6],
                    "GANHO_2": r[7],
                    "GANHO_3": r[8],
                    "GANHO_4": r[9],
                    "DESABILITA_COINS": ""
                }
                for r in cur.fetchall()
            ]

            cur.execute(gerador_alteracao)
            cur.execute(select_alteracao)

            alteracoes = [
                {
                    "ID_META": "",
                    "INDICADOR": r[0],
                    "DATA_INICIO": r[1],
                    "DATA_FIM": r[2],
                    "VALOR_META": r[3],
                    "ATRIBUTOS": r[4],
                    "ATIVO": r[5],
                    "GANHO_1": r[6],
                    "GANHO_2": r[7],
                    "GANHO_3": r[8],
                    "GANHO_4": r[9],
                    "DESABILITA_COINS": ""
                }
                for r in cur.fetchall()
            ]

            cur.execute(gerador_drops)
            cur.execute(gerador_update_coletado)

            CONN.commit()

            return importacoes, alteracoes

        except Exception as e:
            CONN.rollback()
            notify(f"Erro ao gerar importacoes/alteracoes: {e}")
            raise

        finally:
            if cur is not None:
                cur.close()

def update_importado_sistema_matriz():
    with pyodbc.connect(CONNECTION_STRING) as CONN:
        cur = None
        try:
            cur = CONN.cursor()
            cur.execute("""
                update robbysonmatriz.dbo.sistema_matriz 
                set importado = 1,
                    data_importacao = getdate()
                where 
                    importado = 0
                    and importacao_valida = 1
                    and matriz_coletada = 1
                    and periodo = dateadd(d, 1, eomonth(getdate(), -1))
                    and ativo in (0, 1, 3)
                    and atributo in (select distinct atributo from robbysonmatriz.dbo.publico_piloto_sistema_matriz (nolock))
            """)
            CONN.commit()
        except Exception as e:
            CONN.rollback()
            notify(f"Erro ao atualizar sistema matriz: {e}")
        finally:
            if cur is not None:
                cur.close()