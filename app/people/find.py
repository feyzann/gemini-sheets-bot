"""Person finding logic with phone and fuzzy name matching."""

import re
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
from loguru import logger


class PersonFinder:
    """Find people by phone number or fuzzy name matching."""
    
    def __init__(self, people_data: List[Dict[str, Any]]):
        self.people_data = people_data
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number by removing spaces and special characters."""
        if not phone:
            return ""
        
        # Remove all non-digit characters except +
        normalized = re.sub(r'[^\d+]', '', phone)
        
        # Ensure E.164 format (starts with +)
        if normalized.startswith('+'):
            return normalized
        elif normalized.startswith('90'):  # Turkish country code
            return '+' + normalized
        elif normalized.startswith('0'):  # Local format
            return '+90' + normalized[1:]
        else:
            return '+' + normalized
    
    def _fuzzy_match(self, text1: str, text2: str, threshold: float = 0.85) -> bool:
        """Check if two strings match with fuzzy matching."""
        if not text1 or not text2:
            return False
        
        # Normalize strings (lowercase, trim)
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        # Calculate similarity ratio
        ratio = SequenceMatcher(None, text1, text2).ratio()
        return ratio >= threshold
    
    def find_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Find person by exact phone number match."""
        if not phone:
            return None
        
        normalized_phone = self._normalize_phone(phone)
        logger.debug(f"Searching for phone: {normalized_phone}")
        
        for person in self.people_data:
            person_phone = self._normalize_phone(person.get('phone', ''))
            if person_phone == normalized_phone:
                logger.info(f"Found person by phone match: {person.get('full_name', 'Unknown')}")
                return person
        
        logger.debug(f"No phone match found for: {normalized_phone}")
        return None
    
    def find_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find person by fuzzy name matching."""
        if not name:
            return None
        
        logger.debug(f"Searching for name: {name}")
        
        best_match = None
        best_ratio = 0.0
        
        for person in self.people_data:
            full_name = person.get('full_name', '')
            preferred_name = person.get('preferred_name', '')
            
            # Check full name
            if full_name and self._fuzzy_match(name, full_name):
                ratio = SequenceMatcher(None, name.lower(), full_name.lower()).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = person
            
            # Check preferred name
            if preferred_name and self._fuzzy_match(name, preferred_name):
                ratio = SequenceMatcher(None, name.lower(), preferred_name.lower()).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = person
        
        if best_match:
            logger.info(f"Found person by name match (ratio: {best_ratio:.2f}): {best_match.get('full_name', 'Unknown')}")
        else:
            logger.debug(f"No name match found for: {name}")
        
        return best_match
    
    def find_person(self, user_phone: Optional[str] = None, user_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find person with priority: phone exact match, then name fuzzy match."""
        # First try phone match
        if user_phone:
            person = self.find_by_phone(user_phone)
            if person:
                return person
        
        # Then try name match
        if user_name:
            person = self.find_by_name(user_name)
            if person:
                return person
        
        return None
    
    def extract_name_from_message(self, message: str) -> Optional[str]:
        """Extract potential name from message using simple patterns."""
        if not message:
            return None
        
        # Simple patterns to extract names
        patterns = [
            r'(?:ben|benim adım|adım)\s+([A-ZÇĞIİÖŞÜa-zçğıiöşü]+(?:\s+[A-ZÇĞIİÖŞÜa-zçğıiöşü]+)*)',
            r'([A-ZÇĞIİÖŞÜ][a-zçğıiöşü]+(?:\s+[A-ZÇĞIİÖŞÜ][a-zçğıiöşü]+)*)\s+(?:ben|olacağım|olarak)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 2:  # Basic validation
                    logger.debug(f"Extracted name from message: {name}")
                    return name
        
        return None
    
    def build_facts(self, person: Dict[str, Any]) -> Dict[str, Any]:
        """Build facts object from person data."""
        return {
            "person_id": person.get("person_id", ""),
            "full_name": person.get("full_name", ""),
            "preferred_name": person.get("preferred_name", ""),
            "school": person.get("school", ""),
            "department": person.get("department", ""),
            "email": person.get("email", ""),
            "phone": person.get("phone", ""),
            "locale": person.get("locale", ""),
            "profile_text": person.get("profile_text", "")
        }
