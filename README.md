# Simulación de propagación de virus (ABM + SIR)

Aplicación local para una exposición universitaria. Cada persona es un agente fijo
en una red de contactos Watts-Strogatz. Los estados son **S** (sano), **I**
(infectado) y **R** (recuperado).

## Archivos

| Archivo | Función |
| --- | --- |
| `modelo.py` | Agentes, red, reglas SIR, semilla y DataCollector |
| `app.py` | Interfaz Solara, controles, gráficos y exportación |
| `ui.css` | Estilos adaptables del tablero de simulación |
| `requirements.txt` | Dependencias compatibles con Python 3.11 o 3.12+ |
| `README.md` | Instrucciones de instalación, uso y exposición |

## Para compartir

Envía `virus_abm_para_compartir.zip` a tu compañero. Debe descomprimirlo en
una carpeta de su laptop. El ZIP contiene únicamente los cinco archivos de
la tabla; no necesita copiar tu carpeta `.venv`, el CSV ni las imágenes.
Cada laptop crea su propio entorno e instala las dependencias una vez con
acceso a Internet. Se recomienda Python 3.11 de 64 bits.

## Instalación en PowerShell

Desde PowerShell, dentro de la carpeta descomprimida:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m solara run app.py
```

Si `py -3.11` no existe, instala Python 3.11 o usa `python -m venv .venv`
si `python --version` muestra una versión compatible.
Solara muestra la dirección local al iniciar; por defecto es
`http://localhost:8765`. Abre esa dirección en el navegador.
Para cerrar el servidor, pulsa `Ctrl+C` en PowerShell.

## Uso

La página empieza en **día 0**, con 95 sanos y 5 infectados. **Iniciar /
continuar** reproduce la simulación; **Pausar** detiene el reloj; **Siguiente
día** ejecuta un único `modelo.step()`; **Reiniciar** crea un modelo nuevo y
aplica los parámetros del panel. El deslizador cambia la velocidad de
reproducción. Los cambios de parámetros se aplican solo al reiniciar.
El panel señala cuando hay cambios pendientes; **Aplicar y reiniciar** está
junto a los parámetros.

**Guardar** crea en la carpeta del proyecto:

- `resultados_simulacion.csv`, con `Dia,Sanos,Infectados,Recuperados`;
- `grafica_curva_epidemica.png`, con Seaborn;
- `grafica_red_final.png`, con la red en su estado actual;
- `grafica_apilada.png`, con la distribución SIR.

Se pueden guardar resultados durante la simulación o al finalizar.

## Para defender el código

1. `Persona.step()` representa el comportamiento individual. Una persona
   infectada intenta recuperarse con probabilidad 0.3 desde el día de
   recuperación configurado; una sana revisa a sus vecinos y puede infectarse
   con la probabilidad configurada por vecino infectado. Recuperada es inmune.
2. `ModeloVirus` construye la red con NetworkX, coloca un agente en cada
   nodo de Mesa y utiliza `self.agents.shuffle_do("step")` para activar a todos
   una vez por día, en orden aleatorio.
3. El `DataCollector` guarda el estado inicial y una fila después de cada
   día. Por eso el CSV empieza en el día 0 y siempre suma la población total.
4. La interfaz llama `modelo.step()` y después lee el estado y el
   `DataCollector`; el modelo no conoce los botones ni las figuras.
5. **Iniciar** activa el reloj Play de ipywidgets en el navegador. **Pausar**
   lo detiene. **Siguiente día** lo pausa y ejecuta exactamente un paso.
6. **Reiniciar** construye un `ModeloVirus` nuevo con los parámetros del panel,
   limpia la historia y vuelve al día 0.
7. El diseño de la red se calcula con `nx.spring_layout` una sola vez por
   instancia. Cada actualización cambia solo los colores de los nodos.
8. La gráfica SIR lee las filas ya recopiladas y crece después de cada paso.
9. La misma semilla reproduce la red, el orden de activación y las decisiones
   aleatorias. Cambiar la semilla puede cambiar la trayectoria.
10. Cuando no quedan infectados, o se alcanza el máximo de días, el reloj
    se detiene y el resumen, la red y las gráficas permanecen visibles.

## Versión sin comentarios

Las versiones nuevas `modelo.py` y `app.py` están comentadas para estudiarlas.
Para preparar una copia limpia, duplica esos dos archivos en el editor y
elimina los comentarios que empiezan por `#`, tanto en líneas completas como
al final de una línea de código.
Conserva las cadenas entre comillas (incluidos docstrings) y la indentación.
El código ejecutable será el mismo.

## Problemas frecuentes

- `No module named mesa` o `No module named solara`: instala las dependencias
  con el Python de `.venv` y arranca con `python -m solara` de ese entorno.
- `py` o `python` no se reconoce: instala Python 3.11 y vuelve a abrir
  PowerShell.
- El puerto 8765 está ocupado: inicia con
  `.\.venv\Scripts\python.exe -m solara run app.py --port 8766` y abre la URL indicada.
- Conexiones inválidas: Watts-Strogatz exige un número par de conexiones,
  al menos 2 y menor que la población.
- Los parámetros no cambian durante la ejecución: pulsa **Reiniciar** para
  aplicar los valores escritos.

En Python 3.11, `requirements.txt` instala Mesa 3.3.1. Mesa 3.5.1 requiere
Python 3.12 o superior, y el mismo archivo selecciona esa versión en esos
intérpretes. No se usan CanvasGrid ni los módulos antiguos `mesa.time`.
