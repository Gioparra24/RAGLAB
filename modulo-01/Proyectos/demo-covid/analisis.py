"""Análisis reproducible de casos positivos reportados en Boyacá.

Ejecutar desde la raíz del repositorio:
    python modulo-01/proyectos/demo-covid/analisis.py

El CSV no se copia ni se modifica. El script crea un tablero HTML y gráficos en
docs/proyectos/demo-covid/.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


RAIZ_REPO = Path(__file__).resolve().parents[3]
RUTA_CSV = (
    RAIZ_REPO
    / "modulo-01"
    / "Proyectos"
    / "Casos_positivos_de_COVID-19_en_Colombia._20261031.csv"
)
RUTA_TABLERO = RAIZ_REPO / "docs" / "proyectos" / "demo-covid"
RUTA_GRAFICOS = RUTA_TABLERO / "graficos"
FUENTE = (
    "https://www.datos.gov.co/Salud-y-Protecci-n-Social/"
    "Casos-positivos-de-COVID-19-en-Colombia-/gt2j-8ykr/about_data"
)
DEPARTAMENTO = "BOYACA"
COL_FECHA = "fecha reporte web"
COL_ID = "ID de caso"
COL_DEPARTAMENTO = "Nombre departamento"
COL_MUNICIPIO = "Nombre municipio"


def cargar_y_validar() -> tuple[pd.DataFrame, dict[str, object]]:
    """Lee el CSV, imprime un perfil estructural y prepara el subconjunto válido."""
    if not RUTA_CSV.is_file():
        raise FileNotFoundError(f"No se encontró el CSV esperado: {RUTA_CSV}")

    datos = pd.read_csv(RUTA_CSV, dtype={COL_ID: "string"}, low_memory=False)
    requeridas = {COL_FECHA, COL_ID, COL_DEPARTAMENTO, COL_MUNICIPIO}
    faltantes = requeridas.difference(datos.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas necesarias: {sorted(faltantes)}")

    print("PERFIL ESTRUCTURAL DEL CSV")
    print(f"Archivo: {RUTA_CSV}")
    print(f"Filas: {len(datos):,} | Columnas: {len(datos.columns)}")
    print("Columnas y tipos pandas:")
    for nombre, tipo in datos.dtypes.items():
        print(f"  {nombre}: {tipo}")
    print("Faltantes por columna:")
    print(datos.isna().sum().to_string())
    print(f"Filas exactamente duplicadas: {datos.duplicated().sum():,}")
    ids_presentes = datos[COL_ID].dropna().str.strip()
    ids_presentes = ids_presentes[ids_presentes.ne("")]
    print(f"IDs de caso duplicados (no vacíos): {ids_presentes.duplicated().sum():,}")

    departamento = datos[COL_DEPARTAMENTO].astype("string").str.strip().str.upper()
    boyaca = datos.loc[departamento.eq(DEPARTAMENTO)].copy()
    if boyaca.empty:
        disponibles = sorted(departamento.dropna().unique().tolist())
        raise ValueError(
            f"El filtro {DEPARTAMENTO!r} no encontró filas. "
            f"Departamentos observados: {disponibles}"
        )

    boyaca[COL_FECHA] = pd.to_datetime(boyaca[COL_FECHA], errors="coerce")
    fecha_invalida = int(boyaca[COL_FECHA].isna().sum())
    id_vacio = boyaca[COL_ID].isna() | boyaca[COL_ID].str.strip().eq("")
    id_duplicado = boyaca[COL_ID].duplicated(keep="first")
    municipio_vacio = boyaca[COL_MUNICIPIO].isna() | boyaca[COL_MUNICIPIO].astype("string").str.strip().eq("")
    validos = boyaca.loc[
        boyaca[COL_FECHA].notna() & ~id_vacio & ~id_duplicado
    ].copy()
    if validos.empty:
        raise ValueError("No quedaron casos con fecha e ID válidos tras limpiar los datos.")

    perfil = {
        "filas_csv": len(datos),
        "columnas": len(datos.columns),
        "duplicados_exactos": int(datos.duplicated().sum()),
        "id_duplicados": int(ids_presentes.duplicated().sum()),
        "departamentos": sorted(departamento.dropna().unique().tolist()),
        "filas_departamento": len(boyaca),
        "fechas_invalidas": fecha_invalida,
        "ids_vacios": int(id_vacio.sum()),
        "filas_excluidas_id_duplicado": int(id_duplicado.sum()),
        "municipios_vacios": int(municipio_vacio.sum()),
        "completos": validos,
    }
    return datos, perfil


def generar_resultados(perfil: dict[str, object]) -> dict[str, object]:
    casos = perfil["completos"]
    assert isinstance(casos, pd.DataFrame)
    casos["mes"] = casos[COL_FECHA].dt.to_period("M")
    mensual = casos.groupby("mes")[COL_ID].nunique().sort_index()
    rango_meses = pd.period_range(mensual.index.min(), mensual.index.max(), freq="M")
    mensual = mensual.reindex(rango_meses, fill_value=0)
    municipios = (
        casos.assign(municipio=casos[COL_MUNICIPIO].astype("string").str.strip())
        .dropna(subset=["municipio"])
        .groupby("municipio")[COL_ID]
        .nunique()
        .sort_values(ascending=False)
        .head(10)
        .sort_values()
    )

    RUTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(12, 5.5))
    plt.plot(mensual.index.astype(str), mensual.values, marker="o", linewidth=1.8)
    plt.title("Casos únicos por mes de fecha de reporte web — Boyacá")
    plt.xlabel("Mes de reporte")
    plt.ylabel("Casos (ID único)")
    plt.xticks(rotation=60, ha="right")
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(RUTA_GRAFICOS / "casos_mensuales.png", dpi=150)
    plt.close()

    plt.figure(figsize=(10, max(5, len(municipios) * 0.42)))
    plt.barh(municipios.index.astype(str), municipios.values, color="#168aad")
    plt.title("Diez municipios con más casos reportados — Boyacá")
    plt.xlabel("Casos (ID único)")
    plt.ylabel("Municipio")
    plt.grid(axis="x", alpha=0.25)
    plt.tight_layout()
    plt.savefig(RUTA_GRAFICOS / "casos_por_municipio.png", dpi=150)
    plt.close()

    total = int(casos[COL_ID].nunique())
    mes_pico = str(mensual.idxmax())
    valor_pico = int(mensual.max())
    inicio = casos[COL_FECHA].min().date().isoformat()
    fin = casos[COL_FECHA].max().date().isoformat()
    meses_cero = int((mensual == 0).sum())
    return {
        "mensual": mensual,
        "municipios": municipios,
        "total": total,
        "mes_pico": mes_pico,
        "valor_pico": valor_pico,
        "inicio": inicio,
        "fin": fin,
        "meses": len(mensual),
        "meses_cero": meses_cero,
    }


def generar_tablero(perfil: dict[str, object], r: dict[str, object]) -> None:
    # Leer únicamente para el perfil de faltantes; nunca se muestran registros.
    originales = pd.read_csv(RUTA_CSV, dtype={COL_ID: "string"}, low_memory=False)
    faltantes = originales.isna().sum()
    detalle_faltantes = "\n".join(
        f"<li><code>{escape(str(c))}</code>: {int(n):,}</li>"
        for c, n in faltantes.items()
    )
    mensual = r["mensual"]
    previo = mensual.shift(1)
    comparables = mensual[(previo.notna()) & (previo > 0)]
    if len(comparables):
        variacion = ((comparables / previo.loc[comparables.index]) - 1) * 100
        indicador_variacion = f"{variacion.iloc[-1]:+.1f}% en el último mes comparable"
    else:
        indicador_variacion = "No calculable: no hay meses consecutivos comparables con base positiva"
    hallazgo = (
        f"El mes con más casos dentro del periodo fue {escape(str(r['mes_pico']))}, "
        f"con {int(r['valor_pico']):,} casos únicos reportados."
    )
    RUTA_TABLERO.mkdir(parents=True, exist_ok=True)
    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Casos COVID-19 reportados en Boyacá</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:1050px;margin:2rem auto;padding:0 1rem;color:#17212b;line-height:1.55}}
h1,h2{{color:#075985}} .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem}}
.card,section{{border:1px solid #d9e2ec;border-radius:10px;padding:1rem;margin:1rem 0;background:#fff}}
.metric{{font-size:1.35rem;font-weight:700}} img{{width:100%;height:auto}} small{{color:#475569}}
</style></head><body>
<h1>Casos positivos de COVID-19 reportados en Boyacá</h1>
<p><strong>Pregunta:</strong> ¿Cómo evolucionó mes a mes el número de casos reportados?</p>
<p><strong>Departamento:</strong> Boyacá (normalizado como <code>BOYACA</code>) ·
<strong>Periodo observado tras limpieza:</strong> {r['inicio']} a {r['fin']}.</p>
<div class="cards">
<div class="card"><small>Casos únicos con fecha válida en el periodo</small><div class="metric">{int(r['total']):,}</div></div>
<div class="card"><small>Variación frente al mes anterior (último mes comparable)</small><div class="metric">{escape(indicador_variacion)}</div></div>
</div>
<section><h2>Hallazgo</h2><p>{hallazgo}</p></section>
<section><h2>Evolución mensual</h2><img src="graficos/casos_mensuales.png" alt="Gráfico de líneas de casos únicos por mes"></section>
<section><h2>Distribución territorial</h2><img src="graficos/casos_por_municipio.png" alt="Gráfico de barras de los diez municipios con más casos"></section>
<section><h2>Cómo se calcularon</h2><p>Se seleccionó <code>Nombre departamento</code> tras quitar espacios y normalizar mayúsculas.
La fecha de agrupación es <code>fecha reporte web</code>, convertida a fecha con errores convertidos en valores ausentes.
Se contaron IDs únicos en cada mes calendario y por municipio; se excluyeron registros sin fecha válida, sin ID de caso o con ID repetido (se conserva la primera aparición). El tablero presenta {int(r['meses']):,} meses con registros.</p>
<p><strong>Limitaciones de limpieza:</strong> {int(perfil['fechas_invalidas']):,} fechas inválidas, {int(perfil['ids_vacios']):,} IDs vacíos y {int(perfil['filas_excluidas_id_duplicado']):,} filas con ID repetido en Boyacá fueron excluidos. Municipios vacíos identificados: {int(perfil['municipios_vacios']):,}. Los meses calendario sin casos se incluyen como cero.</p>
<p><strong>Perfil del archivo:</strong> {int(perfil['filas_csv']):,} filas, {int(perfil['columnas'])} columnas, {int(perfil['duplicados_exactos']):,} filas exactamente duplicadas; faltantes por columna:</p><ul>{detalle_faltantes}</ul>
<p>La fecha de reporte no equivale necesariamente a la fecha de contagio o inicio de síntomas. Estos datos describen los registros contenidos en el CSV y no deben interpretarse por sí solos como incidencia real ni como cobertura completa de casos.</p></section>
<section><h2>Fuente</h2><p><a href="{FUENTE}">Portal Nacional de Datos Abiertos: Casos positivos de COVID-19 en Colombia</a></p>
<p><strong>Indicadores:</strong> total de casos únicos válidos en el periodo y variación porcentual mensual respecto al mes anterior (no calculable si el mes previo es cero).</p>
<p><strong>Alcance del archivo:</strong> este CSV contiene {int(perfil['filas_csv']):,} filas y un único valor observado de departamento. Los resultados representan el archivo local suministrado, no necesariamente la totalidad nacional del conjunto publicado.</p></section>
</body></html>"""
    (RUTA_TABLERO / "index.html").write_text(html, encoding="utf-8")


def main() -> None:
    _, perfil = cargar_y_validar()
    resultados = generar_resultados(perfil)
    generar_tablero(perfil, resultados)
    print("\nRESUMEN DEL ANÁLISIS")
    print(f"Departamento: {DEPARTAMENTO}")
    print(f"Periodo: {resultados['inicio']} a {resultados['fin']}")
    print(f"Casos únicos incluidos: {resultados['total']:,}")
    print(f"Mes pico: {resultados['mes_pico']} ({resultados['valor_pico']:,} casos)")
    print(f"Tablero: {RUTA_TABLERO / 'index.html'}")
    print(f"Gráficos: {RUTA_GRAFICOS}")


if __name__ == "__main__":
    main()