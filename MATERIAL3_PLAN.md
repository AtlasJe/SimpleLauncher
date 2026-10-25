# Plan de aplicación de Material 3 — Simple Launcher

Este documento define el siguiente trabajo visual de la primera publicación pública de Simple Launcher.

Referencia oficial que se debe seguir:

<https://m3.material.io/styles>

La paleta de color dinámico ya está implementada. El trabajo pendiente debe aplicar las instrucciones oficiales de Material 3 para:

- Elevación
- Iconos
- Movimiento
- Forma
- Tipografía

## Prompt para continuar el desarrollo

```text
Analiza el proyecto Simple Launcher y aplica las instrucciones oficiales de Material Design 3 que aparecen en:

https://m3.material.io/styles

El color dinámico ya está implementado. No lo reemplaces. Conserva la apariencia adaptable al sistema, el color semilla #72C3CB y el logo SVG/ICO actual.

Aplica únicamente las partes pendientes de la página de Material 3:

1. Elevación
Sigue las recomendaciones oficiales para crear jerarquía entre fondos, superficies, tarjetas, diálogos y elementos flotantes. Usa las superficies, bordes y contrastes apropiados para que la elevación funcione en modo claro y oscuro.

2. Iconos
Sigue las recomendaciones oficiales de Material 3 para tamaño, alineación, legibilidad, consistencia y uso de iconos. Revisa la navegación, botones, acciones, estados, errores, confirmaciones y elementos de archivos.

3. Movimiento
Sigue las recomendaciones oficiales de Material 3 para transiciones, duración, continuidad y respuesta visual. Añade movimiento únicamente donde ayude a entender cambios de vista, carga, selección, progreso o apertura de diálogos. No bloquees la interfaz ni ralentices descargas.

4. Forma
Sigue las recomendaciones oficiales de Material 3 para radios, formas, agrupación y jerarquía visual. Unifica botones, campos, tarjetas, paneles, diálogos y controles sin hacer que la interfaz ocupe espacio innecesario.

5. Tipografía
Sigue las recomendaciones oficiales de Material 3 para escala tipográfica, tamaños, pesos, contraste, jerarquía y legibilidad. Mantén Nunito como fuente principal y una fuente monoespaciada únicamente para la consola y los registros.

Revisa todas las secciones del launcher: Onboarding, Jugar, Versiones, Mods, Modrinth, Modpacks, Capturas, Skins, Ajustes, Backup y Reset Total.

Restricciones:
- No cambies la lógica de Minecraft, Fabric, perfiles, mundos, skins, slots, backups ni importaciones.
- No elimines funciones existentes.
- No vuelvas a añadir selectores manuales de modo claro/oscuro.
- No reemplaces el logo SVG ni el ICO.
- No modifiques datos del usuario.
- Crea un backup antes de editar.
- Mantén el tema separado de la lógica principal.
- Reutiliza componentes y evita código duplicado.

Antes de terminar:
- Comprueba la sintaxis.
- Verifica que el launcher abra sin traceback.
- Comprueba las secciones principales y el onboarding.
- Comprueba la apariencia adaptable en modo claro y oscuro.
- Resume los cambios, el backup creado y cualquier limitación.
- No compiles el .exe hasta verificar primero el código.
```

## Versiones del plan

### Base actual

- Sistema de color dinámico.
- Apariencia adaptable al sistema.
- Logo SVG para la interfaz.
- ICO actualizado para ventana y ejecutable.
- Fuente Nunito integrada.
- Onboarding y sistema de backups unificado.

### Siguiente iteración — Material 3 visual

- Aplicación de elevación.
- Unificación de formas y radios.
- Corrección y normalización de iconos.
- Jerarquía tipográfica completa.
- Movimiento y transiciones ligeras.
- Revisión visual de todas las secciones.

### Iteración posterior — Ajuste y accesibilidad

- Corrección de contrastes.
- Revisión de textos pequeños o poco legibles.
- Estados claros para botones, casillas, campos y diálogos.
- Mejor adaptación al redimensionar la ventana.
- Revisión de espaciado y densidad visual.

### Estabilización

- Pruebas completas del launcher.
- Corrección de errores visuales restantes.
- Verificación de onboarding, backups, perfiles, slots, skins y modpacks.
- Optimización de cargas y transiciones.
- Compilación de una nueva versión estable solamente después de las pruebas.

## Regla de trabajo

Cada versión debe tener su propio backup, cambios verificables y una compilación independiente. No se deben mezclar modificaciones visuales con cambios de funcionalidad sin documentarlos.
