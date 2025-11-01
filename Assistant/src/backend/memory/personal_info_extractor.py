# -*- coding: utf-8 -*-
"""
Extractor de Información Personal
Detecta y extrae automáticamente información personal de las conversaciones
"""

import re
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from src.backend.utils.unified_logger import get_unified_logger

logger = get_unified_logger("PERSONAL_INFO_EXTRACTOR")

class PersonalInfoExtractor:
    """Extrae información personal de conversaciones automáticamente"""
    
    def __init__(self, session_dir: Optional[Path] = None):
        self.session_dir = session_dir or Path(".")
        self.profile_file = self.session_dir / "user_profile.json"
        self.patterns = {
            "favorite_food": [
                r"mi comida favorita (?:es|son) (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"me gusta(?:n)? (?:comer|la|las|los|el) (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"(?:adoro|amo) (?:comer|la|las|los|el) (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"mi platillo favorito (?:es|son) (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"(?:disfruto|prefiero) (?:comer|la|las|los|el) (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))"
            ],
            "name": [
                r"me llamo (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"mi nombre es (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"soy (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"(?:mi|el) nombre (?:es|:) (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))"
            ],
            "age": [
                r"tengo (\d+) años",
                r"mi edad es (\d+)",
                r"(?:soy de|tengo) (\d+) años"
            ],
            "profession": [
                r"trabajo (?:como|de) (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"soy (.+?) de profesión",
                r"me dedico a (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"mi trabajo es (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"mi profesión es (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))"
            ],
            "hobbies": [
                r"me gusta (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"mi hobby es (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"disfruto (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"(?:practico|hago) (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))"
            ],
            "location": [
                r"vivo en (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"soy de (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"mi ciudad es (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))"
            ],
            "favorite_color": [
                r"mi color favorito (?:es|son) (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"me gusta el color (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"prefiero el color (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"mi color preferido (?:es|son) (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"(?:adoro|amo) el color (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))",
                r"es el (.+?)(?:\.|$|,|\s*(?:y|pero|aunque))"
            ]
        }
        
        # Palabras a filtrar para evitar falsos positivos
        self.filter_words = {
            "name": ["estudiante", "profesor", "doctor", "ingeniero", "programador"],
            "favorite_food": ["nada", "todo", "cualquier", "cosa"],
            "profession": ["casa", "aquí", "allí"],
            "hobbies": ["nada", "todo", "cualquier"],
            "location": ["aquí", "allí", "casa"],
            "favorite_color": ["nada", "todo", "cualquier", "cosa"]
        }
    
    def extract_from_message(self, message: str) -> Dict[str, Any]:
        """
        Extrae información personal de un mensaje
        
        Args:
            message: Mensaje del usuario
            
        Returns:
            Dict con información extraída
        """
        extracted = {}
        message_lower = message.lower().strip()
        
        if not message_lower or len(message_lower) < 3:
            return extracted
        
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                try:
                    match = re.search(pattern, message_lower, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        
                        # Validar y limpiar el valor extraído
                        if self._is_valid_extraction(category, value):
                            extracted[category] = self._clean_extracted_value(value)
                            logger.info(f"📝 Información extraída - {category}: {extracted[category]}")
                            break
                except Exception as e:
                    logger.warning(f"Error en patrón {pattern}: {e}")
                    continue
        
        return extracted
    
    def _is_valid_extraction(self, category: str, value: str) -> bool:
        """
        Valida si una extracción es válida
        
        Args:
            category: Categoría de información
            value: Valor extraído
            
        Returns:
            True si es válido
        """
        if not value or len(value.strip()) < 2:
            return False
            
        value_clean = value.strip().lower()
        
        # Filtrar palabras no válidas
        if category in self.filter_words:
            for filter_word in self.filter_words[category]:
                if filter_word in value_clean:
                    return False
        
        # Validaciones específicas por categoría
        if category == "name":
            # Evitar nombres muy largos o con caracteres extraños
            if len(value_clean) > 50 or any(char in value_clean for char in ['@', '#', '$', '%']):
                return False
                
        elif category == "favorite_food":
            # Evitar respuestas muy vagas
            if len(value_clean) < 3 or value_clean in ['si', 'no', 'tal vez', 'quizás']:
                return False
                
        elif category == "age":
            # Validar rango de edad razonable
            try:
                age = int(value)
                if age < 5 or age > 120:
                    return False
            except ValueError:
                return False
        
        return True
    
    def _clean_extracted_value(self, value: str) -> str:
        """
        Limpia y normaliza un valor extraído
        
        Args:
            value: Valor a limpiar
            
        Returns:
            Valor limpio
        """
        # Remover espacios extra y caracteres especiales al final
        cleaned = value.strip().rstrip('.,;:!?')
        
        # Capitalizar primera letra para nombres
        if cleaned and len(cleaned) > 1:
            cleaned = cleaned[0].upper() + cleaned[1:]
            
        return cleaned
    
    def update_user_profile(self, user_profile: Dict[str, Any], 
                          extracted_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza el perfil del usuario con información extraída
        
        Args:
            user_profile: Perfil actual del usuario
            extracted_info: Nueva información extraída
            
        Returns:
            Perfil actualizado
        """
        if not extracted_info:
            return user_profile
            
        # Asegurar que existe la sección de perfil
        if "profile" not in user_profile:
            user_profile["profile"] = {}
            
        profile = user_profile["profile"]
        updates_made = []
        
        # Actualizar información personal
        for key, value in extracted_info.items():
            if key == "favorite_food":
                profile["favorite_food"] = value
                updates_made.append(f"comida favorita: {value}")
                
            elif key == "name":
                profile["name"] = value
                updates_made.append(f"nombre: {value}")
                
            elif key == "age":
                try:
                    profile["age"] = int(value) if str(value).isdigit() else value
                    updates_made.append(f"edad: {value}")
                except ValueError:
                    profile["age"] = value
                    updates_made.append(f"edad: {value}")
                    
            elif key == "profession":
                profile["profession"] = value
                updates_made.append(f"profesión: {value}")
                
            elif key == "location":
                profile["location"] = value
                updates_made.append(f"ubicación: {value}")
                
            elif key == "hobbies":
                if "hobbies" not in profile:
                    profile["hobbies"] = []
                if value not in profile["hobbies"]:
                    profile["hobbies"].append(value)
                    updates_made.append(f"hobby: {value}")
        
        # Agregar timestamp de última actualización
        import datetime
        profile["last_updated"] = datetime.datetime.now().isoformat()
        
        if updates_made:
            logger.info(f"✅ Perfil actualizado: {', '.join(updates_made)}")
        
        return user_profile
    
    def extract_and_update(self, message: str) -> Dict[str, Any]:
        """
        Extrae información personal de un mensaje y actualiza el perfil del usuario
        
        Args:
            message: Mensaje del usuario
            
        Returns:
            Información extraída
        """
        # Extraer información del mensaje
        extracted_info = self.extract_from_message(message)
        
        if not extracted_info:
            return {}
            
        # Cargar perfil existente
        user_profile = self._load_user_profile()
        
        # Actualizar perfil
        updated_profile = self.update_user_profile(user_profile, extracted_info)
        
        # Guardar perfil actualizado
        self._save_user_profile(updated_profile)
        
        return extracted_info
    
    def _load_user_profile(self) -> Dict[str, Any]:
        """Carga el perfil del usuario desde archivo"""
        try:
            if self.profile_file.exists():
                with open(self.profile_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading user profile: {e}")
        
        return {"profile": {}}
    
    def _save_user_profile(self, profile: Dict[str, Any]) -> None:
        """Guarda el perfil del usuario en archivo"""
        try:
            self.profile_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.profile_file, 'w', encoding='utf-8') as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving user profile: {e}")
    
    def get_relevant_info(self, query: str) -> str:
        """
        Obtiene información personal relevante para una consulta
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Información personal relevante
        """
        user_profile = self._load_user_profile()
        return self.get_relevant_personal_info(query, user_profile)

    def get_relevant_personal_info(self, query: str, user_profile: Dict[str, Any]) -> str:
        """
        Obtiene información personal relevante para una consulta
        
        Args:
            query: Consulta del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Información personal relevante como string
        """
        if "profile" not in user_profile:
            return ""
            
        profile = user_profile["profile"]
        relevant_info = []
        query_lower = query.lower()
        
        # Detectar qué información es relevante según la consulta
        if any(word in query_lower for word in ["comida", "favorita", "comer", "platillo", "plato"]):
            if "favorite_food" in profile:
                relevant_info.append(f"La comida favorita del usuario es {profile['favorite_food']}")
        
        if any(word in query_lower for word in ["nombre", "llamo", "soy"]):
            if "name" in profile:
                relevant_info.append(f"El nombre del usuario es {profile['name']}")
        
        if any(word in query_lower for word in ["edad", "años", "viejo", "joven"]):
            if "age" in profile:
                relevant_info.append(f"El usuario tiene {profile['age']} años")
        
        if any(word in query_lower for word in ["trabajo", "profesión", "dedico"]):
            if "profession" in profile:
                relevant_info.append(f"El usuario trabaja como {profile['profession']}")
        
        if any(word in query_lower for word in ["vivo", "ciudad", "lugar", "ubicación"]):
            if "location" in profile:
                relevant_info.append(f"El usuario vive en {profile['location']}")
        
        if any(word in query_lower for word in ["gusta", "hobby", "disfruto", "tiempo libre"]):
            if "hobbies" in profile and profile["hobbies"]:
                hobbies_str = ", ".join(profile["hobbies"])
                relevant_info.append(f"Al usuario le gusta: {hobbies_str}")
        
        if any(word in query_lower for word in ["color", "favorito", "preferido", "gusta"]):
            if "favorite_color" in profile:
                relevant_info.append(f"El color favorito del usuario es {profile['favorite_color']}")
        
        return ". ".join(relevant_info) if relevant_info else ""

def test_extractor():
    """Función de prueba para el extractor"""
    extractor = PersonalInfoExtractor()
    
    test_messages = [
        "Hola, me llamo Santiago y mi comida favorita es la pizza",
        "Mi nombre es Ana y trabajo como ingeniera",
        "Soy Carlos, tengo 25 años y vivo en Madrid",
        "Me gusta jugar fútbol y mi hobby es la fotografía"
    ]
    
    print("🧪 PROBANDO EXTRACTOR DE INFORMACIÓN PERSONAL")
    print("=" * 50)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📝 Mensaje {i}: {message}")
        extracted = extractor.extract_from_message(message)
        print(f"✅ Extraído: {extracted}")
    
    print("\n🎉 Pruebas completadas")

if __name__ == "__main__":
    test_extractor()