from pathlib import Path
from datetime import datetime
import xlwt

MAX_ROWS = 1900

BASE_DIR = Path(__file__).resolve().parent
PENDING_DIR = BASE_DIR / "pendentes"


COLUMNS = [
    "ID_META",
    "INDICADOR",
    "DATA_INICIO",
    "DATA_FIM",
    "VALOR_META",
    "ATRIBUTOS",
    "ATIVO",
    "GANHO_1",
    "GANHO_2",
    "GANHO_3",
    "GANHO_4",
    "DESABILITA_COINS",
]


def _create_xls(rows, file_path):
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet("Plan1")
    text_style = xlwt.easyxf(num_format_str="@")

    for col, column_name in enumerate(COLUMNS):
        sheet.write(0, col, column_name, text_style)

    for row_index, row in enumerate(rows, start=1):
        for col_index, column_name in enumerate(COLUMNS):
            value = str(row.get(column_name, ""))
            sheet.write(row_index, col_index, value, text_style)

    workbook.save(str(file_path))

def _generate_batches(rows):
    """
    Divide os registros em lotes de no máximo MAX_ROWS.
    """

    for start in range(0, len(rows), MAX_ROWS):
        yield rows[start:start + MAX_ROWS]


def generate_files(importacoes, alteracoes):
    PENDING_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    generated_files = []

    for tipo, rows in (
        ("importacao", importacoes),
        ("alteracao", alteracoes),
    ):
        if not rows:
            continue

        for batch_number, batch in enumerate(
            _generate_batches(rows),
            start=1
        ):
            file_name = (
                f"{timestamp}_{tipo}_{batch_number:03d}.xls"
            )

            file_path = PENDING_DIR / file_name

            _create_xls(batch, file_path)

            generated_files.append(file_path)

    return generated_files