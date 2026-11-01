# ADR: micro frontends en Chicago Road Risk

**Estado:** aceptada · **Fecha:** 2026-11-01

## Contexto

El feedback de visualización sugiere estudiar una arquitectura de micro frontends.
La aplicación es una SPA React + MapLibre GL JS servida por Nginx en un único
contenedor, desarrollada por un solo equipo, con un mapa WebGL compartido por
todos los paneles (el panel de tramos resalta cuadras en el mapa, el simulador
elige puntos en él, la tabla y el mapa se seleccionan en ambos sentidos).

## Opciones evaluadas

| Opción | Qué implica | Riesgo para la app |
| --- | --- | --- |
| Module Federation (`@originjs/vite-plugin-federation`) | Un *host* y varios *remotes* con build y despliegue propios; React, Zustand y MapLibre como dependencias *singleton* compartidas en tiempo de ejecución | Alto: más contenedores o rutas en Nginx, versiones de React/MapLibre que deben coincidir exactamente, el plugin para Vite 5 tiene limitaciones en desarrollo, y el mapa y los stores compartidos son justo lo que más cuesta federar |
| Web Components / iframes por panel | Aislamiento fuerte | Alto: el mapa compartido y la selección bidireccional dejarían de ser triviales |
| **Módulos por funcionalidad con carga diferida** (elegida) | Cada pestaña del panel (Tramos, Analítica, Simulador, Modelo) es un módulo con su propio *chunk* (`React.lazy` + `Suspense`); comparten React, stores y mapa por importación | Bajo: un único build y despliegue, mismo comportamiento |

## Decisión

Se adopta la tercera opción. Cada pestaña es una frontera de módulo independiente
(se descarga sólo cuando se abre: p. ej. `SegmentPriorityPanel-*.js` ≈ 2,5 kB
brotli, `ModelMetricsPanel-*.js` ≈ 2 kB) y se comunica con el resto sólo a través
de los stores (`useUiStore`, `useMapStore`) y la API. Esto reproduce las
propiedades útiles de los micro frontends (módulos con fronteras explícitas,
carga independiente) sin el coste operativo de federar bundles.

## Consecuencias

* Si en el futuro un equipo distinto mantuviera un panel, el paso a Module
  Federation consistiría en publicar ese módulo como *remote* sin cambiar su
  contrato (props vacías + stores + API).
* No hay versionado independiente por panel: un cambio en un panel requiere
  reconstruir el frontend completo (aceptable con un solo equipo).
