# Sistema de Control de Versiones - IIMP-WEB

## Descripción

Este proyecto implementa un sistema de versionado automático que mantiene un registro de cambios y actualiza automáticamente los footers en todas las páginas HTML.

## Archivos del Sistema

- `version.json` - Configuración principal de versión y changelog
- `update_version.py` - Script para actualizar versiones automáticamente
- `VERSION_CONTROL.md` - Esta documentación

## Estructura de version.json

```json
{
  "version": "1.00",
  "build": "001",
  "release_date": "2024-01-15",
  "changes": [
    {
      "version": "1.00",
      "date": "2024-01-15",
      "description": "Descripción del cambio",
      "fixes": ["Lista de correcciones"],
      "features": ["Lista de nuevas características"]
    }
  ]
}
```

## Uso del Sistema

### Actualizar Versión Automáticamente

```bash
python update_version.py
```

El script te guiará a través de:
1. Selección del tipo de actualización (patch/minor/major)
2. Descripción de los cambios
3. Actualización automática de footers en HTML
4. Generación del changelog

### Tipos de Versión

- **Patch (1.00 → 1.01)**: Correcciones de errores
- **Minor (1.00 → 1.10)**: Nuevas características
- **Major (1.00 → 2.00)**: Cambios importantes o breaking changes

### Archivos HTML Actualizados Automáticamente

- `frontend/index.html`
- `frontend/checkout.html`
- `frontend/thank-you.html`

## Footers

Todos los footers siguen el formato:
```html
<footer class="mt-16 py-4 text-center">
    <p class="text-xs text-gray-400 font-light">
        Desarrollado por Goodlinks - v1.00
    </p>
</footer>
```

## Historial de Cambios

El historial completo se mantiene en `version.json` en la sección `changes`, ordenado cronológicamente (más reciente primero).

## Buenas Prácticas

1. **Siempre usar el script** para actualizar versiones
2. **Describir claramente** los cambios realizados
3. **Probar en desarrollo** antes de actualizar en producción
4. **Hacer commit** del `version.json` actualizado
5. **Documentar breaking changes** en actualizaciones major

## Integración con Producción

Para aplicar cambios en producción:

1. Ejecutar `python update_version.py`
2. Verificar que todos los archivos HTML se actualizaron
3. Probar la aplicación localmente
4. Hacer commit y push de los cambios
5. Desplegar en producción

## Ejemplo de Flujo de Trabajo

```bash
# 1. Realizar cambios en el código
# 2. Actualizar versión
python update_version.py

# 3. Verificar cambios
git diff

# 4. Commit y push
git add .
git commit -m "feat: nueva funcionalidad - v1.01"
git push

# 5. Desplegar en producción
```

## Troubleshooting

### Error: No se encuentra version.json
- Asegúrate de ejecutar el script desde la raíz del proyecto

### Los footers no se actualizan
- Verifica que los archivos HTML existen en las rutas especificadas
- Revisa que el patrón del footer coincida con el esperado

### Problemas de encoding
- Todos los archivos usan UTF-8
- Asegúrate de que tu editor mantenga la codificación