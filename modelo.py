"""Modelo SIR de personas conectadas por una red Watts-Strogatz."""

import networkx as nx
from mesa import Model
from mesa.datacollection import DataCollector
from mesa.discrete_space import FixedAgent, Network


class Persona(FixedAgent):
    """Una persona fija en un nodo de la red de contactos."""

    def __init__(self, model, cell, estado_inicial="S"):
        super().__init__(model)
        self.cell = cell
        self.estado = estado_inicial
        self.tiempo_infectado = 0

    def step(self):
        # Se mantiene el orden original: primero recuperación, luego contagio.
        if self.estado == "I":
            self.tiempo_infectado += 1
            if (
                self.tiempo_infectado >= self.model.dias_recuperacion
                and self.random.random() < self.model.probabilidad_recuperacion
            ):
                self.estado = "R"
                return

        if self.estado == "S":
            for vecino in self.cell.neighborhood.agents:
                if (
                    vecino.estado == "I"
                    and self.random.random() < self.model.probabilidad_contagio
                ):
                    self.estado = "I"
                    self.tiempo_infectado = 0
                    break


class ModeloVirus(Model):
    """Simulación SIR: S -> I -> R, con activación aleatoria por día."""

    def __init__(
        self,
        *,
        num_personas=100,
        num_infectados_iniciales=5,
        probabilidad_contagio=0.15,
        dias_recuperacion=7,
        conexiones=6,
        reconexion=0.1,
        max_dias=50,
        seed=42,
    ):
        if not 2 <= num_personas <= 500:
            raise ValueError("La población debe estar entre 2 y 500.")
        if not 0 <= num_infectados_iniciales <= num_personas:
            raise ValueError("Los infectados iniciales deben estar entre 0 y la población.")
        if not 0 <= probabilidad_contagio <= 1 or not 0 <= reconexion <= 1:
            raise ValueError("Las probabilidades deben estar entre 0 y 1.")
        if dias_recuperacion < 1 or max_dias < 1:
            raise ValueError("Los días de recuperación y el máximo deben ser positivos.")
        if conexiones < 2 or conexiones >= num_personas or conexiones % 2:
            raise ValueError("Las conexiones deben ser pares, al menos 2 y menores que la población.")

        super().__init__(rng=seed)
        self.num_personas = num_personas
        self.num_infectados_iniciales = num_infectados_iniciales
        self.probabilidad_contagio = probabilidad_contagio
        self.probabilidad_recuperacion = 0.3  # Regla original: 30 % tras el mínimo de días.
        self.dias_recuperacion = dias_recuperacion
        self.conexiones = conexiones
        self.reconexion = reconexion
        self.max_dias = max_dias
        self.seed = seed
        self.dia = 0
        self.nuevos_contagios = 0
        self.nuevos_recuperados = 0
        self.pico_infectados = num_infectados_iniciales
        self.dia_pico = 0

        # NetworkX construye la red; cada celda de Mesa aloja una persona.
        self.red = nx.watts_strogatz_graph(
            n=num_personas, k=conexiones, p=reconexion, seed=seed
        )
        self.grid = Network(self.red, capacity=1, random=self.random)
        self.personas_por_nodo = {}
        for nodo in self.red.nodes:
            estado = "I" if nodo < num_infectados_iniciales else "S"
            self.personas_por_nodo[nodo] = Persona(self, self.grid[nodo], estado)

        # La primera fila corresponde al día 0 y cada step añade una fila más.
        self.datacollector = DataCollector(
            model_reporters={
                "Sanos": lambda m: m.contar("S"),
                "Infectados": lambda m: m.contar("I"),
                "Recuperados": lambda m: m.contar("R"),
            }
        )
        self.datacollector.collect(self)
        self.running = num_infectados_iniciales > 0

    def contar(self, estado):
        return sum(persona.estado == estado for persona in self.agents)

    def conteos(self):
        return {estado: self.contar(estado) for estado in ("S", "I", "R")}

    def step(self):
        if not self.running or self.dia >= self.max_dias:
            return

        antes = self.conteos()
        # Equivale al RandomActivation del proyecto anterior.
        self.agents.shuffle_do("step")
        self.dia += 1
        despues = self.conteos()
        self.nuevos_contagios = antes["S"] - despues["S"]
        self.nuevos_recuperados = despues["R"] - antes["R"]
        if despues["I"] > self.pico_infectados:
            self.pico_infectados = despues["I"]
            self.dia_pico = self.dia
        self.datacollector.collect(self)
        self.running = despues["I"] > 0 and self.dia < self.max_dias
