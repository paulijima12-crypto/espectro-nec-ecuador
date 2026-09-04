import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import io
import matplotlib.lines as mlines
from matplotlib.backends.backend_pdf import PdfPages
import os
import io
import csv
from datetime import datetime
from PIL import Image

# 1. Configuración de la página Web/Móvil
st.set_page_config(page_title="Generador de Espectros NEC", layout="wide")
st.title("📱 Generador de Espectros de Diseño - NEC-SE-DS")

# 2. TABLAS NORMATIVAS NEC-15 PARA AUTOMATIZACIÓN
map_Z = {"I": 0.15, "II": 0.25, "III": 0.30, "IV": 0.35, "V": 0.40, "VI": 0.50}
opciones = {
    'Z': ["I", "II", "III", "IV", "V", "VI"],
    'Suelo': ["A", "B", "C", "D", "E", "F"],
    'n': ["1.80", "2.48"],
    'Ct': ["0.043", "0.055", "0.073", "0.085"],
    'alpha': ["0.75", "0.80", "0.90"]
}

# Matrices de coeficientes de sitio
tabla_Fa = {
    "A": {"I": 0.90, "II": 0.90, "III": 0.90, "IV": 0.90, "V": 0.90, "VI": 0.90},
    "B": {"I": 1.00, "II": 1.00, "III": 1.00, "IV": 1.00, "V": 1.00, "VI": 1.00},
    "C": {"I": 1.20, "II": 1.20, "III": 1.10, "IV": 1.10, "V": 1.10, "VI": 1.10},
    "D": {"I": 1.60, "II": 1.40, "III": 1.20, "IV": 1.20, "V": 1.10, "VI": 1.10},
    "E": {"I": 2.60, "II": 1.70, "III": 1.20, "IV": 1.10, "V": 0.90, "VI": 0.90},
    "F": {"I": 1.00, "II": 1.00, "III": 1.00, "IV": 1.00, "V": 1.00, "VI": 1.00}
}
tabla_Fd = {
    "A": {"I": 0.90, "II": 0.90, "III": 0.90, "IV": 0.90, "V": 0.90, "VI": 0.90},
    "B": {"I": 1.00, "II": 1.00, "III": 1.00, "IV": 1.00, "V": 1.00, "VI": 1.00},
    "C": {"I": 1.40, "II": 1.30, "III": 1.10, "IV": 1.10, "V": 1.10, "VI": 1.10},
    "D": {"I": 2.00, "II": 1.60, "III": 1.40, "IV": 1.20, "V": 1.11, "VI": 1.00},
    "E": {"I": 3.20, "II": 2.10, "III": 1.50, "IV": 1.20, "V": 1.10, "VI": 1.10},
    "F": {"I": 1.00, "II": 1.00, "III": 1.00, "IV": 1.00, "V": 1.00, "VI": 1.00}
}
tabla_Fs = {"A": 0.75, "B": 0.75, "C": 0.85, "D": 1.28, "E": 1.62, "F": 1.00}


# --- BARRA LATERAL: DATOS DE ENTRADA ---
with st.sidebar:
    st.header("📥 Datos de Entrada")
    
    # Menú de Referencias Visuales
    with st.expander("📚 Ver Tablas de Referencia"):
        param_ref = st.selectbox("Seleccione el parámetro a consultar:", ['Z', 'n', 'Suelo', 'Fa', 'Fd', 'Fs', 'Ct', 'alpha'])
        img_path = f"tabla_{param_ref}.png" if param_ref != 'Suelo' else "tabla_suelo.png"
        if os.path.exists(img_path):
            st.image(img_path, use_container_width=True)
        else:
            st.error(f"⚠️ Guarda la imagen '{img_path}' en la misma carpeta.")
            
    st.divider()

    Z_zona = st.selectbox("Parámetro Z (Zona):", opciones['Z'], index=4)
    Suelo = st.selectbox("Parámetro Suelo:", opciones['Suelo'], index=3)
    
    # Automatización: Leemos las matrices según la selección actual
    fa_calc = tabla_Fa[Suelo][Z_zona]
    fd_calc = tabla_Fd[Suelo][Z_zona]
    fs_calc = tabla_Fs[Suelo]

    st.markdown("*(Los factores de sitio se autocompletan, pero puedes editarlos manualmente)*")
    Fa = st.number_input("Parámetro Fa:", value=float(fa_calc), step=0.01)
    Fd = st.number_input("Parámetro Fd:", value=float(fd_calc), step=0.01)
    Fs = st.number_input("Parámetro Fs:", value=float(fs_calc), step=0.01)
    
    st.divider()
    n_str = st.selectbox("Parámetro n:", opciones['n'], index=1)
    r = st.number_input("Parámetro r:", value=1.00, step=0.1)
    h = st.number_input("Parámetro h (Altura):", value=10.26, step=0.1)
    Ct_str = st.selectbox("Parámetro Ct:", opciones['Ct'], index=1)
    alpha_str = st.selectbox("Parámetro alpha:", opciones['alpha'], index=0)
    Ta_E = st.number_input("Parámetro Ta_E (ETABS):", value=0.83, step=0.01)
    I_val = st.number_input("Parámetro I (Importancia):", value=1.30, step=0.1)
    R = st.number_input("Parámetro R:", value=5.0, step=0.5)
    phi_p = st.number_input("Parámetro phi_p:", value=1.00, step=0.1)
    phi_e = st.number_input("Parámetro phi_e:", value=1.00, step=0.1)

# Conversiones a float
Z = map_Z.get(Z_zona, 0.40)
n = float(n_str)
Ct = float(Ct_str)
alpha = float(alpha_str)

# --- LÓGICA DE CÁLCULO ---
val_Z_Fa = Z * Fa
To = 0.1 * Fs * (Fd / Fa)
Tc = 0.55 * Fs * (Fd / Fa)
Tl = 2.4 * Fd
TaN = Ct * (h ** alpha)

def calcular_sa_interseccion(t_val):
    if t_val <= Tc:
        return n * Z * Fa
    elif t_val <= Tl:
        return n * Z * Fa * ((Tc / t_val) ** r)
    else:
        return n * Z * Fa * ((Tc / Tl) ** r) 

Sa_TaN = calcular_sa_interseccion(TaN)
Sa_TaE = calcular_sa_interseccion(Ta_E)
V_TaN = (I_val * Sa_TaN) / (R * phi_p * phi_e)
V_TaE = (I_val * Sa_TaE) / (R * phi_p * phi_e)

# Generar arrays para gráfica
puntos_clave = [0, To, Tc, TaN, Ta_E, Tl]
puntos_uniformes = np.arange(0, Tl + 0.05, 0.05).tolist() 
todos_puntos = sorted(list(set(puntos_clave + puntos_uniformes)))
T_arr = np.array([p for p in todos_puntos if p <= Tl]) 
Sa_el = np.array([calcular_sa_interseccion(t) for t in T_arr])
Sa_in = (Sa_el * I_val) / (R * phi_p * phi_e)

# --- PANEL PRINCIPAL ---
st.subheader("⚙️ Parámetros Calculados")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Z", f"{Z:.2f}")
col2.metric("Z*Fa", f"{val_Z_Fa:.3f} g")
col3.metric("To", f"{To:.3f} s")
col4.metric("Tc", f"{Tc:.3f} s")
col5.metric("Tl", f"{Tl:.3f} s")

colA, colB, colC, colD = st.columns(4)
colA.metric("TaN", f"{TaN:.3f} s")
colB.metric("Sa(TaN)", f"{Sa_TaN:.3f} g")
colC.metric("TaE", f"{Ta_E:.3f} s")
colD.metric("Sa(TaE)", f"{Sa_TaE:.3f} g")

# --- PESTAÑAS (TABS) ---
tab1, tab2, tab3 = st.tabs(["📈 Gráfica", "📊 Tabla de Valores", "🗄️ Registro de Pruebas"])

with tab1:
    # ==========================================
        # SECCIÓN DE GRAFICACIÓN MEJORADA
        # ==========================================
        fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
        
        # Curvas principales
        ax.plot(T_arr, Sa_el, 'r-', label='Espectro elástico')
        ax.plot(T_arr, Sa_in, '#2c7fb8', label='Espectro inelástico')
        
        # Estilo de la "cajita" para que los números sean legibles
        box_style = dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='none', alpha=0.8)

        # 1. Marcadores para TaN (Naranja)
        color_tan = '#FFA500' 
        ax.plot(TaN, Sa_TaN, marker='o', color=color_tan, markersize=8, zorder=5)
        ax.plot([TaN, TaN], [0, Sa_TaN], color=color_tan, linestyle='--', linewidth=1.5)
        ax.plot([0, TaN], [Sa_TaN, Sa_TaN], color=color_tan, linestyle='--', linewidth=1.5)
        
        ax.annotate(f"TaN={TaN:.3f}", xy=(TaN, 0), xytext=(0, 5), textcoords="offset points", 
                    color=color_tan, weight='bold', ha='center', va='bottom', bbox=box_style)
        ax.annotate(f"Sa(TaN)={Sa_TaN:.3f}", xy=(TaN, Sa_TaN), xytext=(0, 10), textcoords="offset points", 
                    color=color_tan, weight='bold', ha='center', va='bottom', bbox=box_style)

        # 2. Marcadores para TaE (Magenta)
        color_tae = 'm' 
        ax.plot(Ta_E, Sa_TaE, marker='o', color=color_tae, markersize=8, zorder=5)
        ax.plot([Ta_E, Ta_E], [0, Sa_TaE], color=color_tae, linestyle='-.', linewidth=1.5)
        ax.plot([0, Ta_E], [Sa_TaE, Sa_TaE], color=color_tae, linestyle='-.', linewidth=1.5)
        
        ax.annotate(f"TaE={Ta_E:.3f}", xy=(Ta_E, 0), xytext=(0, 5), textcoords="offset points", 
                    color=color_tae, weight='bold', ha='center', va='bottom', bbox=box_style)
        ax.annotate(f"Sa(TaE)={Sa_TaE:.3f}", xy=(Ta_E, Sa_TaE), xytext=(0, 10), textcoords="offset points", 
                    color=color_tae, weight='bold', ha='center', va='bottom', bbox=box_style)

        # Ajustes visuales de la gráfica
        ax.set_xlim(left=0, right=Tl * 1.05) 
        ax.set_ylim(bottom=0, top=max(Sa_el) * 1.25) 
        ax.set_title("Espectro de Diseño NEC-SE-DS", fontsize=12, fontweight='bold')
        ax.set_xlabel("Periodo T (s)")
        ax.set_ylabel("Sa (g)")
        ax.grid(True, linestyle=':', alpha=0.6)
        
        # 3. Leyenda personalizada
        handle_el = mlines.Line2D([], [], color='red', linestyle='-', label='Espectro elástico')
        handle_in = mlines.Line2D([], [], color='#2c7fb8', linestyle='-', label='Espectro inelástico')
        handle_ta_nec = mlines.Line2D([], [], color=color_tan, linestyle='--', label='Ta NEC')
        handle_sa_nec = mlines.Line2D([], [], color=color_tan, linestyle='--', label='Sa NEC')
        handle_ta_e = mlines.Line2D([], [], color=color_tae, linestyle='-.', label='Ta ETABS')
        handle_sa_e = mlines.Line2D([], [], color=color_tae, linestyle='-.', label='Sa ETABS')

        ax.legend(handles=[handle_el, handle_in, handle_ta_nec, handle_sa_nec, handle_ta_e, handle_sa_e],
                  title="LEYENDA", title_fontproperties={'weight':'bold'}, loc='upper right', 
                  edgecolor='black', framealpha=1.0)
        
        # Mostrar la gráfica en Streamlit
        st.pyplot(fig)

        # ==========================================
        # BOTÓN DE EXPORTACIÓN A PDF
        # ==========================================
        buffer_pdf = io.BytesIO()
        fig.savefig(buffer_pdf, format="pdf", bbox_inches="tight")
        buffer_pdf.seek(0)

        st.markdown("---")
        st.download_button(
            label="📄 Descargar Gráfica en PDF",
            data=buffer_pdf,
            file_name="Grafica_Espectro_NEC.pdf",
            mime="application/pdf"
        )

with tab2:
    # Mostrar tabla con Pandas (Corregido el warning width='stretch')
    df_tabla = pd.DataFrame({'T [s]': T_arr, 'Sa Elástico [g]': Sa_el, 'Sa Inelástico [g]': Sa_in})
    st.dataframe(df_tabla.style.format("{:.3f}"), width='stretch')

with tab3:
    filename = "base_datos_variables.csv"
    if os.path.exists(filename):
        df_bd = pd.read_csv(filename)
        # Corregido el warning width='stretch'
        st.dataframe(df_bd, width='stretch')
    else:
        st.info("Aún no hay proyectos guardados en el registro.")

# --- BOTONES DE EXPORTACIÓN (Para celulares) ---
st.divider()
st.subheader("💾 Exportar y Guardar")
col_btn1, col_btn2, col_btn3 = st.columns(3)

# Botón 1: CSV
csv_data = df_tabla.to_csv(index=False).encode('utf-8')
col_btn1.download_button(label="📥 Descargar Tabla (CSV)", data=csv_data, file_name='espectro_tabla.csv', mime='text/csv')

# Botón 2: PDF
pdf_buffer = io.BytesIO()
with PdfPages(pdf_buffer) as pdf:
    pdf.savefig(fig)
    fig_datos = plt.figure(figsize=(8.27, 11.69))
    txt = "REPORTE SÍSMICO - ESPECTRO DE DISEÑO NEC-SE-DS\n" + "="*65 + "\n\n"
    txt += f"1. DATOS DE ENTRADA:\n{'-'*30}\n"
    txt += f"Zona Z: {Z_zona} ({Z}), Suelo: {Suelo}, n: {n}, Ct: {Ct}, alpha: {alpha}\n"
    txt += f"Fa: {Fa}, Fd: {Fd}, Fs: {Fs}, r: {r}, h: {h}\n"
    txt += f"\n2. PUNTOS DE CONTROL:\n{'-'*30}\n"
    txt += f"TaN: {TaN:.3f} s  |  Sa(TaN): {Sa_TaN:.3f} g  |  V(TaN): {V_TaN:.3f}\n"
    txt += f"TaE: {Ta_E:.3f} s  |  Sa(TaE): {Sa_TaE:.3f} g  |  V(TaE): {V_TaE:.3f}\n"
    txt += f"\nGenerado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    fig_datos.text(0.1, 0.95, txt, fontsize=11, fontfamily='monospace', va='top')
    pdf.savefig(fig_datos)
    plt.close(fig_datos)

col_btn2.download_button(label="📄 Descargar Reporte (PDF)", data=pdf_buffer.getvalue(), file_name='reporte_sismico.pdf', mime='application/pdf')

# Botón 3: Guardar en Base de Datos
if col_btn3.button("💾 Guardar en Registro de Pruebas"):
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not os.path.exists(filename) or os.stat(filename).st_size == 0:
            headers = ['Fecha', 'Z_zona', 'n', 'Suelo', 'Fa', 'Fd', 'Fs', 'r', 'h', 'Ct', 'alpha', 'Ta_E', 'I', 'R', 'phi_p', 'phi_e', 'TaN', 'Sa_TaN', 'V_TaN', 'TaE', 'Sa_TaE', 'V_TaE']
            writer.writerow(headers)
        row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), Z_zona, n_str, Suelo, Fa, Fd, Fs, r, h, Ct_str, alpha_str, Ta_E, I_val, R, phi_p, phi_e, round(TaN,3), round(Sa_TaN,3), round(V_TaN,3), round(Ta_E,3), round(Sa_TaE,3), round(V_TaE,3)]
        writer.writerow(row)
    st.success("¡Datos guardados con éxito! Actualiza la página para verlos en la pestaña.")
