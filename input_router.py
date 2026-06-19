"""
Input router for intelligent file type detection and request routing.
Enhances planner with advanced file categorization and routing logic.
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class InputRouter:
    """Intelligently route inputs based on file type and content detection."""
    
    # File type mappings
    CODE_EXTENSIONS = {
        'py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'h', 'hpp',
        'cs', 'php', 'rb', 'go', 'rs', 'swift', 'kt', 'scala', 'groovy',
        'sh', 'bash', 'zsh', 'ps1', 'bat', 'cmd', 'lua', 'vim', 'r',
        'sql', 'pl', 'vb', 'asp', 'erb', 'jinja', 'html', 'css', 'scss',
        'xml', 'json', 'yaml', 'yml', 'toml', 'ini', 'cfg', 'conf'
    }
    
    DOCUMENT_EXTENSIONS = {
        'pdf', 'txt', 'doc', 'docx', 'docm', 'odt', 'rtf', 'tex', 'md',
        'markdown', 'rst', 'adoc', 'asciidoc'
    }
    
    SPREADSHEET_EXTENSIONS = {
        'xls', 'xlsx', 'xlsm', 'ods', 'csv', 'tsv', 'gnumeric'
    }
    
    IMAGE_EXTENSIONS = {
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico', 'tiff'
    }
    
    MEDIA_EXTENSIONS = {
        'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'mp3', 'wav', 'flac',
        'aac', 'm4a', 'ogg', 'wma'
    }
    
    ARCHIVE_EXTENSIONS = {
        'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz', 'iso'
    }

    @classmethod
    def detect_file_type(cls, file_path: str) -> str:
        """Detect file type category."""
        path = Path(file_path)
        ext = path.suffix.lstrip('.').lower()
        
        if ext in cls.CODE_EXTENSIONS:
            return 'code'
        elif ext in cls.DOCUMENT_EXTENSIONS:
            return 'document'
        elif ext in cls.SPREADSHEET_EXTENSIONS:
            return 'spreadsheet'
        elif ext in cls.IMAGE_EXTENSIONS:
            return 'image'
        elif ext in cls.MEDIA_EXTENSIONS:
            return 'media'
        elif ext in cls.ARCHIVE_EXTENSIONS:
            return 'archive'
        else:
            return 'unknown'

    @classmethod
    def is_code_file(cls, file_path: str) -> bool:
        """Check if file is a code file."""
        return cls.detect_file_type(file_path) == 'code'

    @classmethod
    def is_document(cls, file_path: str) -> bool:
        """Check if file is a document."""
        return cls.detect_file_type(file_path) in ('document', 'code', 'spreadsheet')

    @classmethod
    def get_file_description(cls, file_path: str) -> str:
        """Get human-readable file type description."""
        file_type = cls.detect_file_type(file_path)
        descriptions = {
            'code': '💻 Code File',
            'document': '📄 Document',
            'spreadsheet': '📊 Spreadsheet',
            'image': '🖼️ Image',
            'media': '🎬 Media',
            'archive': '📦 Archive',
            'unknown': '📁 File'
        }
        return descriptions.get(file_type, '📁 File')

    @classmethod
    def route_file_action(cls, file_path: str) -> Dict[str, str]:
        """Determine appropriate action for file type."""
        file_type = cls.detect_file_type(file_path)
        
        routes = {
            'code': {
                'action': 'analyze_code',
                'description': 'Code analysis and explanation',
                'suggested_prompt': 'Explain this code, suggest improvements'
            },
            'document': {
                'action': 'analyze_document',
                'description': 'Document reading and summary',
                'suggested_prompt': 'Summarize this document'
            },
            'spreadsheet': {
                'action': 'analyze_spreadsheet',
                'description': 'Data analysis and insights',
                'suggested_prompt': 'Analyze the data and trends'
            },
            'image': {
                'action': 'analyze_image',
                'description': 'Image analysis and description',
                'suggested_prompt': 'Describe what you see in this image'
            },
            'media': {
                'action': 'process_media',
                'description': 'Media processing',
                'suggested_prompt': 'Analyze this media file'
            },
            'archive': {
                'action': 'list_archive',
                'description': 'Archive exploration',
                'suggested_prompt': 'What files are in this archive?'
            },
            'unknown': {
                'action': 'process_file',
                'description': 'File processing',
                'suggested_prompt': 'Process this file'
            }
        }
        
        return routes.get(file_type, routes['unknown'])

    @classmethod
    def analyze_request_context(cls, prompt: str, files: List[str]) -> Dict:
        """Analyze request context and suggest routing."""
        context = {
            'prompt': prompt,
            'file_count': len(files),
            'file_types': {},
            'suggested_action': 'chat',
            'needs_multimodal': False,
            'code_files': [],
            'document_files': [],
            'image_files': [],
            'other_files': []
        }
        
        for file_path in files:
            file_type = cls.detect_file_type(file_path)
            context['file_types'][file_type] = context['file_types'].get(file_type, 0) + 1
            
            if file_type == 'code':
                context['code_files'].append(file_path)
            elif file_type == 'document':
                context['document_files'].append(file_path)
            elif file_type == 'image':
                context['image_files'].append(file_path)
                context['needs_multimodal'] = True
            else:
                context['other_files'].append(file_path)
        
        # Determine suggested action
        if context['image_files']:
            context['suggested_action'] = 'analyze_image'
        elif context['code_files']:
            context['suggested_action'] = 'analyze_code'
        elif context['document_files']:
            context['suggested_action'] = 'analyze_document'
        elif context['file_count'] > 0:
            context['suggested_action'] = 'process_files'
        
        return context

    @classmethod
    def get_routing_summary(cls, files: List[str]) -> str:
        """Get human-readable routing summary."""
        if not files:
            return "No files attached"
        
        file_types = {}
        for file in files:
            ftype = cls.detect_file_type(file)
            file_types[ftype] = file_types.get(ftype, 0) + 1
        
        summary_parts = []
        for ftype, count in sorted(file_types.items()):
            desc = cls.get_file_description(files[0])  # Just for icon
            summary_parts.append(f"{desc.split()[0]} {count} {ftype}{'s' if count > 1 else ''}")
        
        return " + ".join(summary_parts) if summary_parts else "Unknown file type"

    @classmethod
    def should_analyze_with_vision(cls, file_path: str) -> bool:
        """Check if file should be analyzed with vision model."""
        file_type = cls.detect_file_type(file_path)
        return file_type in ('image', 'document')

    @classmethod
    def extract_code_language(cls, file_path: str) -> str:
        """Extract programming language from code file."""
        path = Path(file_path)
        ext = path.suffix.lstrip('.').lower()
        
        language_map = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'jsx': 'javascript',
            'tsx': 'typescript',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'h': 'c',
            'hpp': 'cpp',
            'cs': 'csharp',
            'php': 'php',
            'rb': 'ruby',
            'go': 'go',
            'rs': 'rust',
            'swift': 'swift',
            'kt': 'kotlin',
            'scala': 'scala',
            'sh': 'bash',
            'bash': 'bash',
            'ps1': 'powershell',
            'sql': 'sql',
            'r': 'r',
            'html': 'html',
            'css': 'css',
            'scss': 'scss',
            'json': 'json',
            'yaml': 'yaml',
            'xml': 'xml',
        }
        
        return language_map.get(ext, 'text')
