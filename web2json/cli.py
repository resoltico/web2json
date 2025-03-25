"""Command-line interface for web2json."""
import argparse
import logging
import sys
import os
from typing import Optional, Tuple, List
from pathlib import Path

from .config import PROGRAM, VERSION, DEFAULT_OUTPUT_FOLDER
from .utils.url import validate_url
from .utils.pipeline_runner import process_url, bulk_process_urls
from .utils.logging_config import setup_logging
from .exceptions import Web2JsonError

def show_banner() -> None:
    """Display program banner."""
    print(f"""
{PROGRAM} v{VERSION}
Web page to structured JSON converter
Use -h or --help for usage information
""")

def show_examples() -> str:
    """Return usage examples."""
    return """Examples:
    # Process single URL:
    web2json -u https://example.com/article/12345
    
    # Custom output name:
    web2json -u https://example.com/article/12345 -o article_12345
    
    # Process URLs from file:
    web2json -f urls.txt
    
    # Preserve HTML styles:
    web2json -u https://example.com/article/12345 --preserve-styles
    
    # Enable verbose logging:
    web2json -u https://example.com/article/12345 -v
    
    # Custom output directory:
    web2json -u https://example.com/article/12345 --output-dir ~/web_data"""

def process_single_url(url: str, output_dir: str, custom_name: Optional[str] = None, preserve_styles: bool = False) -> bool:
    """Process single URL to JSON."""
    if not validate_url(url):
        logging.error(f"Invalid URL: {url}")
        return False
        
    logging.info(f"Processing: {url}")
    
    try:
        # Create output path if custom name is provided
        output_path = None
        if custom_name:
            # Ensure the directory exists
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{custom_name}.json")
        else:
            # Pipeline runner will handle filename generation
            os.makedirs(output_dir, exist_ok=True)
            from .utils.filesystem import generate_filename
            dir_path, filename = generate_filename(url, output_dir)
            output_path = os.path.join(dir_path, filename)
        
        # Process the URL
        result = process_url(
            url=url, 
            output_path=output_path,
            preserve_styles=preserve_styles
        )
        
        return result.get('exported', False)
    except Web2JsonError as e:
        logging.error(f"Error processing {url}: {str(e)}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error processing {url}: {str(e)}")
        return False

def process_urls_from_file(urls_file: str, output_dir: str, preserve_styles: bool = False) -> Tuple[int, int]:
    """Process multiple URLs from file."""
    try:
        # Read URLs from file
        with open(urls_file, "r", encoding='utf-8') as file:
            urls = [line.strip() for line in file if line.strip()]
            
        if not urls:
            logging.error(f"No URLs found in file: {urls_file}")
            return (0, 0)
            
        # Validate URLs
        valid_urls = []
        for url in urls:
            if validate_url(url):
                valid_urls.append(url)
            else:
                logging.warning(f"Skipping invalid URL: {url}")
        
        if not valid_urls:
            logging.error("No valid URLs found in file")
            return (0, 0)
            
        # Process valid URLs
        logging.info(f"Processing {len(valid_urls)} URLs from file")
        result = bulk_process_urls(valid_urls, output_dir, preserve_styles)
        
        return (result['success'], result['failure'])
        
    except Exception as e:
        logging.error(f"Error processing URLs file: {str(e)}")
        return (0, 0)

def main() -> int:
    """Main CLI entry point."""
    show_banner()
    
    parser = argparse.ArgumentParser(
        description="Convert web pages into structured JSON format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=show_examples()
    )
    
    input_group = parser.add_argument_group('Input Options')
    input_group.add_argument("-f", "--file", help="File containing URLs (one per line)")
    input_group.add_argument("-u", "--url", help="Single URL to process")
    
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument("-o", "--output", help="Custom output path/name")
    output_group.add_argument("--output-dir", help=f"Output directory (default: {DEFAULT_OUTPUT_FOLDER})",
                            default=DEFAULT_OUTPUT_FOLDER)
    output_group.add_argument("--preserve-styles", action="store_true",
                           help="Preserve HTML style tags")
    
    debug_group = parser.add_argument_group('Debug Options')
    debug_group.add_argument("-v", "--verbose", action="store_true",
                          help="Enable verbose logging")
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if args.url and args.file:
        logging.error("Cannot specify both URL and file")
        parser.print_help()
        return 1
        
    if args.output and not args.url:
        logging.error("Custom output path requires single URL")
        parser.print_help()
        return 1
        
    if not any([args.url, args.file]):
        parser.print_help()
        return 0
        
    try:
        if args.url:
            success = process_single_url(args.url, args.output_dir, args.output, args.preserve_styles)
            return 0 if success else 2
        elif args.file:
            success_count, fail_count = process_urls_from_file(args.file, args.output_dir, args.preserve_styles)
            return 0 if success_count > 0 else (2 if fail_count > 0 else 1)
    except KeyboardInterrupt:
        logging.info("\nOperation cancelled by user")
        return 1
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return 3

if __name__ == "__main__":
    sys.exit(main())
