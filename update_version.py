#!/usr/bin/env python3
"""
Script para actualizar la versión del proyecto IIMP-WEB
Actualiza version.json y los footers en archivos HTML
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List

def load_version_config() -> Dict:
    """Carga la configuración de versión desde version.json"""
    with open('version.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_version_config(config: Dict) -> None:
    """Guarda la configuración de versión en version.json"""
    with open('version.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def increment_version(version: str, increment_type: str = 'patch') -> str:
    """Incrementa la versión según el tipo especificado"""
    parts = version.split('.')
    major, minor = int(parts[0]), int(parts[1])
    
    if increment_type == 'major':
        major += 1
        minor = 0
    elif increment_type == 'minor':
        minor += 1
    
    return f"{major}.{minor:02d}"

def update_html_footers(version: str) -> List[str]:
    """Actualiza los footers en archivos HTML"""
    html_files = [
        'frontend/index.html',
        'frontend/checkout.html',
        'frontend/thank-you.html'
    ]
    
    updated_files = []
    footer_pattern = r'(Desarrollado por Goodlinks - v)[0-9]+\.[0-9]+'
    new_footer = f'Desarrollado por Goodlinks - v{version}'
    
    for file_path in html_files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            updated_content = re.sub(footer_pattern, f'\\g<1>{version}', content)
            
            if updated_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                updated_files.append(file_path)
    
    return updated_files

def add_changelog_entry(config: Dict, version: str, description: str, 
                       fixes: List[str] = None, features: List[str] = None) -> None:
    """Agrega una nueva entrada al changelog"""
    new_entry = {
        "version": version,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "description": description
    }
    
    if fixes:
        new_entry["fixes"] = fixes
    if features:
        new_entry["features"] = features
    
    config["changes"].insert(0, new_entry)

def main():
    """Función principal"""
    print("🔄 Actualizando versión del proyecto IIMP-WEB...")
    
    # Cargar configuración actual
    config = load_version_config()
    current_version = config["version"]
    
    print(f"📋 Versión actual: {current_version}")
    
    # Solicitar tipo de incremento
    print("\n¿Qué tipo de actualización deseas realizar?")
    print("1. Patch (corrección de errores)")
    print("2. Minor (nuevas características)")
    print("3. Major (cambios importantes)")
    
    choice = input("Selecciona una opción (1-3): ").strip()
    
    increment_map = {'1': 'patch', '2': 'minor', '3': 'major'}
    increment_type = increment_map.get(choice, 'patch')
    
    # Incrementar versión
    new_version = increment_version(current_version, increment_type)
    
    # Solicitar descripción del cambio
    description = input(f"\n📝 Descripción de los cambios en v{new_version}: ").strip()
    
    # Actualizar configuración
    config["version"] = new_version
    config["build"] = str(int(config["build"]) + 1).zfill(3)
    config["release_date"] = datetime.now().strftime("%Y-%m-%d")
    
    # Agregar entrada al changelog
    add_changelog_entry(config, new_version, description)
    
    # Actualizar archivos HTML
    updated_files = update_html_footers(new_version)
    
    # Guardar configuración
    save_version_config(config)
    
    print(f"\n✅ Versión actualizada a {new_version}")
    print(f"🏗️  Build: {config['build']}")
    print(f"📅 Fecha: {config['release_date']}")
    
    if updated_files:
        print(f"\n📄 Archivos HTML actualizados:")
        for file in updated_files:
            print(f"   - {file}")
    
    print("\n🎉 ¡Actualización completada!")

if __name__ == "__main__":
    main()