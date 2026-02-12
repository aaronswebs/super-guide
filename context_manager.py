"""
Context Manager for Agent Grounding
Handles loading and managing policy documents and SharePoint sites for agent context
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse


class ContextManager:
    """
    Manages additional context sources for grounding agent responses
    in policy documents and SharePoint sites
    """
    
    # Default context templates for different policy types
    CONTEXT_TEMPLATES = {
        "information_security": {
            "name": "Information Security Policy",
            "description": "Ground responses in information security policies and guidelines"
        },
        "risk_management": {
            "name": "Risk Management Policy",
            "description": "Ground responses in risk management frameworks and policies"
        },
        "compliance_regulatory": {
            "name": "Compliance and Regulatory Documents",
            "description": "Ground responses in compliance and regulatory requirements"
        },
        "data_governance": {
            "name": "Data Governance Policy",
            "description": "Ground responses in data governance policies and standards"
        },
        "ai_ml_governance": {
            "name": "AI/ML Governance Policy",
            "description": "Ground responses in AI/ML governance and ethical guidelines"
        }
    }
    
    def __init__(self):
        """Initialize the context manager"""
        self.context_sources = self._load_enabled_sources()
        self.context_documents = self._load_context_documents()
    
    def _load_enabled_sources(self) -> List[str]:
        """Load enabled context sources from environment"""
        sources_str = os.getenv("CONTEXT_SOURCES", "")
        if not sources_str:
            return []
        
        # Parse comma-separated list
        sources = [s.strip() for s in sources_str.split(",") if s.strip()]
        
        # Validate sources
        valid_sources = []
        for source in sources:
            if source in self.CONTEXT_TEMPLATES:
                valid_sources.append(source)
            else:
                print(f"Warning: Unknown context source '{source}' ignored")
        
        return valid_sources
    
    def _load_context_documents(self) -> Dict[str, str]:
        """Load context documents from files or URLs"""
        documents = {}
        
        for source in self.context_sources:
            env_var = f"CONTEXT_{source.upper()}"
            path_or_url = os.getenv(env_var, "")
            
            if not path_or_url:
                # Use default template description if no document provided
                documents[source] = self._get_default_context(source)
                continue
            
            # Check if it's a URL or file path
            if self._is_url(path_or_url):
                # For SharePoint sites or web URLs
                documents[source] = self._load_from_url(source, path_or_url)
            else:
                # For local file paths
                documents[source] = self._load_from_file(source, path_or_url)
        
        return documents
    
    def _is_url(self, path_or_url: str) -> bool:
        """Check if a string is a URL"""
        try:
            result = urlparse(path_or_url)
            return bool(result.scheme and result.netloc)
        except Exception:
            return False
    
    def _get_default_context(self, source: str) -> str:
        """Get default context description for a source"""
        template = self.CONTEXT_TEMPLATES.get(source, {})
        return f"Use {template.get('name', source)} as a reference for grounding responses. {template.get('description', '')}"
    
    def _load_from_file(self, source: str, file_path: str) -> str:
        """Load context from a local file"""
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"Warning: Context file not found for {source}: {file_path}")
                return self._get_default_context(source)
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                print(f"Warning: Empty context file for {source}: {file_path}")
                return self._get_default_context(source)
            
            template = self.CONTEXT_TEMPLATES.get(source, {})
            return f"{template.get('name', source)} Context:\n\n{content}"
            
        except Exception as e:
            print(f"Error loading context file for {source}: {e}")
            return self._get_default_context(source)
    
    def _load_from_url(self, source: str, url: str) -> str:
        """Load context from a URL (e.g., SharePoint site)"""
        # Note: For SharePoint sites, you would typically need authentication
        # This is a placeholder that includes the URL reference
        template = self.CONTEXT_TEMPLATES.get(source, {})
        return f"{template.get('name', source)} Reference:\n\nRefer to the following resource for {template.get('description', 'policy information').lower()}:\n{url}\n\nNote: When answering questions, consider the policies and guidelines available at this location."
    
    def get_context_string(self) -> str:
        """
        Get the complete context string to append to agent instructions
        
        Returns:
            Formatted context string for all enabled sources
        """
        if not self.context_sources:
            return ""
        
        context_parts = [
            "\n\n=== ADDITIONAL CONTEXT FOR GROUNDING ===\n",
            "Use the following policy documents and resources to ground your responses:\n"
        ]
        
        for source in self.context_sources:
            if source in self.context_documents:
                context_parts.append(f"\n{self.context_documents[source]}\n")
        
        context_parts.append("\n=== END OF ADDITIONAL CONTEXT ===\n")
        
        return "".join(context_parts)
    
    def get_enabled_sources(self) -> List[Dict[str, str]]:
        """
        Get list of enabled context sources with metadata
        
        Returns:
            List of dictionaries containing source information
        """
        sources_info = []
        for source in self.context_sources:
            template = self.CONTEXT_TEMPLATES.get(source, {})
            sources_info.append({
                "id": source,
                "name": template.get("name", source),
                "description": template.get("description", ""),
                "enabled": True
            })
        return sources_info
    
    def get_available_sources(self) -> List[Dict[str, str]]:
        """
        Get list of all available context sources
        
        Returns:
            List of dictionaries containing all available source information
        """
        sources_info = []
        for source, template in self.CONTEXT_TEMPLATES.items():
            sources_info.append({
                "id": source,
                "name": template.get("name", source),
                "description": template.get("description", ""),
                "enabled": source in self.context_sources
            })
        return sources_info
    
    def has_context(self) -> bool:
        """Check if any context sources are enabled"""
        return len(self.context_sources) > 0
