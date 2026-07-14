class DocumentClassifier:
    """
    Classifies documents based on their MIME type and title.
    This classification is used to select the appropriate cleaner and chunking strategy.
    """
    
    @staticmethod
    def classify(mime_type: str, title: str) -> str:
        mime_type = mime_type.lower()
        title_lower = title.lower()
        
        # Explicit Code Extensions
        code_extensions = [
            ".py", ".js", ".ts", ".java", ".go", ".cpp", ".c", ".h", ".cs", 
            ".rb", ".php", ".rs", ".swift", ".kt", ".sql", ".sh", ".bash", ".yml", ".yaml", ".json"
        ]
        
        if any(title_lower.endswith(ext) for ext in code_extensions):
            return "Code"
            
        if mime_type == "application/pdf":
            return "PDF"
            
        if mime_type in [
            "text/csv", 
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.google-apps.spreadsheet"
        ]:
            return "Spreadsheet"
            
        if mime_type == "text/markdown" or title_lower.endswith(".md"):
            return "Markdown"
            
        # Fallback based on mime type
        if mime_type == "text/plain":
            return "Plain Text"
            
        # Default
        return "Plain Text"
