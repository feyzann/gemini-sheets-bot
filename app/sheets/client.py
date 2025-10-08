"""Google Sheets client with caching."""

import os
from typing import List, Dict, Any, Optional
from cachetools import TTLCache
import gspread
from google.oauth2.service_account import Credentials
from loguru import logger
from app.core.config import get_settings

settings = get_settings()


class SheetsClient:
    """Google Sheets client with TTL caching."""
    
    def __init__(self):
        self.cache = TTLCache(maxsize=100, ttl=settings.cache_ttl_ms / 1000)
        self._client: Optional[gspread.Client] = None
        self._sheet: Optional[gspread.Spreadsheet] = None
    
    def _get_client(self) -> gspread.Client:
        """Get authenticated Google Sheets client."""
        if self._client is None:
            try:
                # Set credentials path
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.google_application_credentials
                
                # Authenticate
                scope = [
                    'https://www.googleapis.com/auth/spreadsheets.readonly',
                    'https://www.googleapis.com/auth/drive.readonly'
                ]
                
                creds = Credentials.from_service_account_file(
                    settings.google_application_credentials,
                    scopes=scope
                )
                
                self._client = gspread.authorize(creds)
                logger.info("Google Sheets client authenticated successfully")
                
            except Exception as e:
                logger.error(f"Failed to authenticate Google Sheets client: {e}")
                raise
        
        return self._client
    
    def _get_sheet(self) -> gspread.Spreadsheet:
        """Get the spreadsheet."""
        if self._sheet is None:
            try:
                client = self._get_client()
                self._sheet = client.open_by_key(settings.sheet_id)
                logger.info(f"Opened spreadsheet: {self._sheet.title}")
                
            except Exception as e:
                logger.error(f"Failed to open spreadsheet {settings.sheet_id}: {e}")
                raise
        
        return self._sheet
    
    def get_people_data(self) -> List[Dict[str, Any]]:
        """Get people data from the People sheet with caching."""
        cache_key = "people_data"
        
        # Check cache first
        if cache_key in self.cache:
            logger.debug("Returning people data from cache")
            return self.cache[cache_key]
        
        try:
            sheet = self._get_sheet()
            people_sheet = sheet.worksheet("People")
            
            # Get all values from the range (extract range part after sheet name)
            range_part = settings.range_people.split('!')[1] if '!' in settings.range_people else settings.range_people
            values = people_sheet.get(range_part)
            logger.info(f"Retrieved {len(values)} rows from People sheet")
            
            if not values:
                logger.warning("No data found in People sheet")
                return []
            
            # Convert to list of dictionaries
            # Expected headers: person_id,full_name,preferred_name,school,department,email,phone,locale,profile_doc_id,profile_text,last_updated
            headers = [
                "person_id", "full_name", "preferred_name", "school", "department",
                "email", "phone", "locale", "profile_doc_id", "profile_text", "last_updated"
            ]
            
            people_data = []
            for row in values:
                if len(row) >= len(headers):
                    person = {}
                    for i, header in enumerate(headers):
                        person[header] = row[i] if i < len(row) else ""
                    people_data.append(person)
                else:
                    logger.warning(f"Skipping incomplete row: {row}")
            
            # Cache the result
            self.cache[cache_key] = people_data
            logger.info(f"Cached {len(people_data)} people records")
            
            return people_data
            
        except Exception as e:
            logger.error(f"Failed to get people data: {e}")
            raise


# Global sheets client instance
sheets_client = SheetsClient()
