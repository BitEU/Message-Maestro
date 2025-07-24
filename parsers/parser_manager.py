#!/usr/bin/env python3
"""
Parser manager for automatic detection and loading of parsers
"""
import os
import importlib
import inspect
from typing import List, Optional, Dict, Any

from .base_parser import BaseParser

class ParserManager:
    """Manages and auto-discovers message parsers"""
    
    def __init__(self):
        self.parsers: List[BaseParser] = []
        self._load_parsers()
    
    def _load_parsers(self):
        """Automatically load all parsers from the parsers directory"""
        parsers_dir = os.path.dirname(__file__)
        
        # Get all Python files in parsers directory
        for filename in os.listdir(parsers_dir):
            if filename.endswith('_parser.py') and not filename.startswith('__'):
                module_name = filename[:-3]  # Remove .py extension
                
                try:
                    # Import the module
                    module = importlib.import_module(f'parsers.{module_name}')
                    
                    # Find all BaseParser subclasses in the module
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseParser) and 
                            obj != BaseParser):
                            
                            # Instantiate the parser
                            parser_instance = obj()
                            self.parsers.append(parser_instance)
                            print(f"Loaded parser: {parser_instance.platform_name}")
                            
                except Exception as e:
                    print(f"Error loading parser from {filename}: {e}")
    
    def get_available_parsers(self) -> List[BaseParser]:
        """Get list of all available parsers"""
        return self.parsers.copy()
    
    def get_parser_by_name(self, platform_name: str) -> Optional[BaseParser]:
        """Get parser by platform name"""
        for parser in self.parsers:
            if parser.platform_name.lower() == platform_name.lower():
                return parser
        return None
    
    def detect_parser(self, file_path: str) -> Optional[BaseParser]:
        """
        Automatically detect which parser can handle the given file
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            The appropriate parser or None if no parser can handle the file
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            # Read first few KB to determine file type
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content_sample = f.read(8192)  # Read first 8KB
        except Exception:
            return None
        
        # Try each parser's can_parse method
        for parser in self.parsers:
            try:
                if parser.can_parse(file_path, content_sample):
                    return parser
            except Exception as e:
                print(f"Error checking parser {parser.platform_name}: {e}")
                continue
        
        return None
    
    def get_file_filters(self) -> List[tuple]:
        """
        Get file dialog filters for all parsers
        
        Returns:
            List of tuples (description, extensions) for file dialog
        """
        filters = []
        all_extensions = set()
        
        for parser in self.parsers:
            # Individual parser filter
            extensions = ' '.join(f'*{ext}' for ext in parser.file_extensions)
            filters.append((parser.file_description, extensions))
            all_extensions.update(parser.file_extensions)
        
        # Add "All supported files" filter at the beginning
        if all_extensions:
            all_ext_str = ' '.join(f'*{ext}' for ext in sorted(all_extensions))
            filters.insert(0, ("All supported formats", all_ext_str))
        
        # Add "All files" filter at the end
        filters.append(("All files", "*.*"))
        
        return filters
    
    def get_parser_info(self) -> List[Dict[str, Any]]:
        """Get information about all loaded parsers"""
        info = []
        for parser in self.parsers:
            info.append({
                'platform_name': parser.platform_name,
                'file_extensions': parser.file_extensions,
                'file_description': parser.file_description,
                'class_name': parser.__class__.__name__
            })
        return info