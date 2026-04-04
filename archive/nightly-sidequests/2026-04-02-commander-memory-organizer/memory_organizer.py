#!/usr/bin/env python3
"""
Memory File Organizer
Commander tool for analyzing and organizing OpenClaw memory files
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional
import argparse

class MemoryOrganizer:
    def __init__(self, memory_dir: str = "/root/.openclaw/workspace/memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_files = list(self.memory_dir.glob("2026-*.md"))
        self.data_index = {}
        self.topics_index = {}
        
    def parse_memory_file(self, file_path: Path) -> Dict:
        """Parse a single memory file and extract structured information"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract date from filename
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file_path.name)
        file_date = date_match.group(1) if date_match else "unknown"
        
        # Find sections (## headers)
        sections = re.findall(r'## (.*?)\n(.*?)(?=##|\Z)', content, re.DOTALL)
        
        # Extract mentions (@USER_ID patterns)
        mentions = re.findall(r'<@(\d+)>', content)
        
        # Extract TODO/action items
        todos = re.findall(r'[-*]\s*(.*?)(?:\n|$)', content)
        
        # Extract file paths (Unix-style paths)
        file_paths = re.findall(r'/[\w/.-]+', content)
        
        # Extract commands (code blocks)
        code_blocks = re.findall(r'```(?:.*?)\n(.*?)\n```', content, re.DOTALL)
        
        return {
            'date': file_date,
            'filename': file_path.name,
            'mentions': list(set(mentions)),
            'sections': sections,
            'todos': todos,
            'file_paths': list(set(file_paths)),
            'code_blocks': code_blocks,
            'word_count': len(content.split()),
            'content_preview': content[:200] + "..." if len(content) > 200 else content
        }
    
    def build_index(self):
        """Build comprehensive index of all memory files"""
        self.data_index = {}
        
        for file_path in sorted(self.memory_files, reverse=True):
            if file_path.name.startswith('.'):
                continue
                
            file_data = self.parse_memory_file(file_path)
            self.data_index[file_path.name] = file_data
            
            # Build topics index
            for section_title, section_content in file_data['sections']:
                # Extract keywords from section content
                keywords = re.findall(r'\b[A-Z][a-zA-Z]+\b', section_content)[:5]  # Capitalized words
                for keyword in keywords:
                    if keyword not in self.topics_index:
                        self.topics_index[keyword] = []
                    self.topics_index[keyword].append(file_path.name)
    
    def search_content(self, query: str, limit: int = 5) -> List[Dict]:
        """Search across memory files for content"""
        query = query.lower()
        results = []
        
        for filename, data in self.data_index.items():
            # Search in content preview, sections, and todos
            search_text = " ".join([
                data['content_preview'],
                " ".join([title for title, _ in data['sections']]),
                " ".join(data['todos'])
            ]).lower()
            
            if query in search_text:
                results.append({
                    'filename': filename,
                    'date': data['date'],
                    'matches': len([1 for word in query.split() if word in search_text]),
                    'mentions': data['mentions'],
                    'sections': data['sections'][:3]  # Top 3 sections
                })
        
        return sorted(results, key=lambda x: x['matches'], reverse=True)[:limit]
    
    def get_user_mentions(self, user_id: str) -> List[Dict]:
        """Find all mentions of a specific user"""
        results = []
        
        for filename, data in self.data_index.items():
            if user_id in data['mentions']:
                results.append({
                    'filename': filename,
                    'date': data['date'],
                    'mention_count': data['mentions'].count(user_id)
                })
        
        return sorted(results, key=lambda x: x['date'], reverse=True)
    
    def get_summary_report(self) -> Dict:
        """Generate a summary report of all memory files"""
        total_files = len(self.data_index)
        total_words = sum(data['word_count'] for data in self.data_index.values())
        all_mentions = set()
        all_file_paths = set()
        
        for data in self.data_index.values():
            all_mentions.update(data['mentions'])
            all_file_paths.update(data['file_paths'])
        
        return {
            'total_files': total_files,
            'total_words': total_words,
            'unique_mentions': len(all_mentions),
            'unique_file_paths': len(all_file_paths),
            'date_range': self.get_date_range(),
            'top_topics': self.get_top_topics(10)
        }
    
    def get_date_range(self) -> Dict:
        """Get the date range of memory files"""
        if not self.data_index:
            return {'start': None, 'end': None}
        
        dates = [data['date'] for data in self.data_index.values()]
        return {
            'start': min(dates),
            'end': max(dates)
        }
    
    def get_top_topics(self, limit: int) -> List[Dict]:
        """Get most frequently mentioned topics"""
        topic_counts = {}
        
        for topic, files in self.topics_index.items():
            topic_counts[topic] = len(files)
        
        return sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def generate_report(self, output_format: str = 'text') -> str:
        """Generate formatted report"""
        report = self.get_summary_report()
        
        if output_format == 'json':
            return json.dumps(report, indent=2)
        
        # Text format
        lines = [
            f"# Memory Files Summary Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"## Overview",
            f"- Total files: {report['total_files']}",
            f"- Total words: {report['total_words']}",
            f"- Unique mentions: {report['unique_mentions']}",
            f"- Unique file paths: {report['unique_file_paths']}",
            f"- Date range: {report['date_range']['start']} to {report['date_range']['end']}",
            "",
            f"## Top Topics",
        ]
        
        for topic, count in report['top_topics']:
            lines.append(f"- {topic}: {count} mentions")
            
        lines.extend([
            "",
            f"## Quick Actions",
            f"Search: python memory_organizer.py search <query>",
            f"Mentions: python memory_organizer.py mentions <USER_ID>",
            f"Index: python memory_organizer.py index"
        ])
        
        return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description='Organize and search OpenClaw memory files')
    parser.add_argument('command', choices=['index', 'search', 'mentions', 'summary'], 
                       help='Command to execute')
    parser.add_argument('--query', help='Search query')
    parser.add_argument('--user-id', help='User ID to search for mentions')
    parser.add_argument('--output-format', choices=['text', 'json'], default='text',
                       help='Output format')
    
    args = parser.parse_args()
    
    organizer = MemoryOrganizer()
    organizer.build_index()
    
    if args.command == 'index':
        print("Building memory file index...")
        print(f"Indexed {len(organizer.data_index)} files")
        print(f"Found {len(organizer.topics_index)} unique topics")
        
    elif args.command == 'search':
        if not args.query:
            print("Error: --query required for search command")
            return
        
        results = organizer.search_content(args.query)
        print(f"\nSearch results for '{args.query}':")
        print("-" * 50)
        
        for result in results:
            print(f"\n📁 {result['filename']} ({result['date']})")
            print(f"   Matches: {result['matches']}")
            for section_title, _ in result['sections']:
                print(f"   📂 {section_title}")
            
    elif args.command == 'mentions':
        if not args.user_id:
            print("Error: --user-id required for mentions command")
            return
        
        results = organizer.get_user_mentions(args.user_id)
        print(f"\nMentions for <@{args.user_id}>:")
        print("-" * 50)
        
        if results:
            for result in results:
                print(f"📁 {result['filename']} ({result['date']}) - {result['mention_count']} mentions")
        else:
            print("No mentions found")
    
    elif args.command == 'summary':
        report = organizer.generate_report(args.output_format)
        print(report)

if __name__ == "__main__":
    main()