"""Command-line interface for web2json."""
import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple
from .config import PROGRAM, VERSION, DEFAULT_OUTPUT_FOLDER, MAX_WORKERS
from .core.url_processor import validate_url, fetch_page
from .core.html_parser import parse_content
from .core.json_converter import save_json
from .utils.file_handler import generate_filename
from .utils.logging_config import setup_logging

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
    web2json.py -u https://example.com/article/12345
    
    # Custom output name:
    web2json.py -u https://example.com/article/12345 -o article_12345
    
    # Process URLs from file:
    web2json.py -f urls.txt
    
    # Preserve HTML styles:
    web2json.py -u https://example.com/article/12345 --preserve-styles
    
    # Enable verbose logging:
    web2json.py -u https://example.com/article/12345 -v
    
    # Custom output directory:
    web2json.py -u https://example.com/article/12345 --output-dir ~/web_data"""

def process_single_url(url: str, output_dir: str, custom_name: Optional[str] = None, preserve_styles: bool = False) -> bool:
    """Process single URL to JSON."""
    if not validate_url(url):
        return False
        
    logging.info(f"Processing: {url}")
    html = fetch_page(url)
    if not html:
        return False
        
    try:
        content = parse_content(html, url, preserve_styles)
        dir_path, filename = generate_filename(url, output_dir, custom_name)
        return save_json(content, dir_path, filename)
    except Exception as e:
        logging.error(f"Error processing {url}: {str(e)}")
        return False

def process_urls_from_file(urls_file: str, output_dir: str, preserve_styles: bool = False) -> Tuple[int, int]:
    """Process multiple URLs from file."""
    try:
        with open(urls_file, "r", encoding='utf-8') as file:
            urls = [line.strip() for line in file if line.strip()]
            
        if not urls:
            logging.error(f"No URLs found in file: {urls_file}")
            return (0, 0)
            
        success_count = fail_count = 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for url in urls:
                if validate_url(url):
                    futures.append(
                        executor.submit(process_single_url, url, output_dir, None, preserve_styles)
                    )
                else:
                    fail_count += 1
                    
            for future in futures:
                if future.result():
                    success_count += 1
                else:
                    fail_count += 1
                    
        logging.info(f"Processing complete: {success_count} successful, {fail_count} failed")
        return (success_count, fail_count)
        
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