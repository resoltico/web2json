"""Command-line interface for web2json."""
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

from web2json.core.pipeline import process_url, bulk_process_urls
from web2json.utils.url import validate_url

# Create Typer app
app = typer.Typer(
    help="Web page to structured JSON converter",
    add_completion=False,
)

# Initialize rich console
console = Console()

# Default output directory
DEFAULT_OUTPUT_FOLDER = Path("fetched_jsons")

# Default timeout in seconds
DEFAULT_TIMEOUT = 60

# Exit code constants for better readability and consistency
EXIT_SUCCESS = 0
EXIT_ERROR_GENERAL = 1
EXIT_ERROR_PROCESSING = 2
EXIT_ERROR_UNEXPECTED = 3


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with rich formatting."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )


def show_banner() -> None:
    """Display program banner."""
    version = __import__('web2json').__version__
    console.print(Panel(f"""
[bold blue]web2json v{version}[/bold blue]
[italic]Web page to structured JSON converter[/italic]
    """, expand=False))


@app.command()
def process(
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Single URL to process"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File containing URLs (one per line)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Custom output filename (without extension)"),
    output_dir: Path = typer.Option(
        DEFAULT_OUTPUT_FOLDER, "--output-dir", "-d", help="Directory to save output files"
    ),
    preserve_styles: bool = typer.Option(
        False, "--preserve-styles", help="Preserve HTML style tags"
    ),
    timeout: int = typer.Option(
        DEFAULT_TIMEOUT, "--timeout", "-t", help="Timeout in seconds for operations"
    ),
    max_concurrent: int = typer.Option(
        5, "--max-concurrent", "-c", help="Maximum number of concurrent URL processing tasks"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Process URLs and convert to structured JSON.
    
    For a single URL (--url), the output will be saved as:
      - With --output: [output_dir]/[output].json
      - Without --output: [output_dir]/[auto_generated_name].json
    
    For multiple URLs (--file), each output will be saved with auto-generated names in [output_dir].
    """
    setup_logging(verbose)
    show_banner()
    
    # Validate command line arguments
    if url and file:
        console.print("[bold red]Error:[/bold red] Cannot specify both URL and file")
        raise typer.Exit(code=EXIT_ERROR_GENERAL)
        
    if output and not url:
        console.print("[bold red]Error:[/bold red] Custom output filename (--output) can only be used with a single URL (--url)")
        raise typer.Exit(code=EXIT_ERROR_GENERAL)
        
    if not any([url, file]):
        console.print("[bold red]Error:[/bold red] You must specify either a URL (--url) or a file containing URLs (--file)")
        typer.echo(app.info.help)
        raise typer.Exit(code=EXIT_ERROR_GENERAL)
    
    # Validate timeout value
    if timeout <= 0:
        console.print("[bold red]Error:[/bold red] Timeout must be a positive number")
        raise typer.Exit(code=EXIT_ERROR_GENERAL)
    
    # Validate max_concurrent value
    if max_concurrent <= 0:
        console.print("[bold red]Error:[/bold red] Maximum concurrent tasks must be a positive number")
        raise typer.Exit(code=EXIT_ERROR_GENERAL)
    
    # Ensure output directory exists with proper error handling
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"Output directory: [blue]{output_dir}[/blue]")
    except Exception as e:
        console.print(f"[bold red]Error creating output directory:[/bold red] {str(e)}")
        raise typer.Exit(code=EXIT_ERROR_GENERAL)
    
    try:
        if url:
            # Process a single URL
            process_single_url(
                url=url,
                output=output,
                output_dir=output_dir,
                preserve_styles=preserve_styles,
                timeout=timeout,
                verbose=verbose
            )
        elif file:
            # Process multiple URLs from a file
            process_url_file(
                file=file,
                output_dir=output_dir,
                preserve_styles=preserve_styles,
                timeout=timeout,
                max_concurrent=max_concurrent,
                verbose=verbose
            )
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(code=EXIT_ERROR_GENERAL)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {str(e)}")
        if verbose:
            console.print_exception()
        raise typer.Exit(code=EXIT_ERROR_UNEXPECTED)


def process_single_url(
    url: str,
    output: Optional[str],
    output_dir: Path,
    preserve_styles: bool,
    timeout: int,
    verbose: bool
) -> None:
    """Process a single URL and save the output."""
    if not validate_url(url):
        console.print(f"[bold red]Invalid URL:[/bold red] {url}")
        raise typer.Exit(code=EXIT_ERROR_PROCESSING)
    
    console.print(f"Processing: [blue]{url}[/blue]")
    
    # Set expectations about the output path
    if output:
        output_path = output_dir / f"{output}.json"
        console.print(f"Output will be saved as: [blue]{output_path}[/blue]")
    else:
        console.print(f"Output will be saved in [blue]{output_dir}[/blue] with an auto-generated filename")
        console.print("The exact filename will be shown after processing completes")
    
    # Show timeout information
    console.print(f"Operation timeout: [blue]{timeout}[/blue] seconds")
    
    # Create progress display with elapsed time
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=not verbose,  # Keep progress visible in verbose mode
    ) as progress:
        task = progress.add_task("Fetching and processing content...", total=None)
        
        # Construct output path if provided
        output_path = None
        if output:
            output_path = output_dir / f"{output}.json"
        
        # Process URL
        result = asyncio.run(process_url(
            url=url,
            output_path=output_path,
            output_dir=output_dir,
            preserve_styles=preserve_styles,
            timeout=timeout
        ))
        
        # Mark task as complete
        progress.update(task, completed=True, description="Processing complete")
    
    # Display results
    if result["success"]:
        console.print(f"[green]Success:[/green] Processed {url}")
        console.print(f"Output saved to: [blue]{result['output_path']}[/blue]")
        
        # Show processing time details if available
        if "processing_time" in result:
            console.print(f"Total processing time: [blue]{result['processing_time']:.2f}[/blue] seconds")
            
            if "stages" in result:
                # Create a table for stage timings
                table = Table(title="Processing Stage Times")
                table.add_column("Stage", style="cyan")
                table.add_column("Time (seconds)", style="green")
                
                for stage, time_taken in result["stages"].items():
                    if time_taken is not None:
                        table.add_row(stage.capitalize(), f"{time_taken:.2f}")
                
                console.print(table)
    else:
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(code=EXIT_ERROR_PROCESSING)


def process_url_file(
    file: Path,
    output_dir: Path,
    preserve_styles: bool,
    timeout: int,
    max_concurrent: int,
    verbose: bool
) -> None:
    """Process multiple URLs from a file."""
    try:
        # Read URLs from file with proper error handling
        file_path = Path(file)
        if not file_path.exists():
            console.print(f"[bold red]Error:[/bold red] File not found: {file}")
            raise typer.Exit(code=EXIT_ERROR_GENERAL)
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                # Try with a different encoding if UTF-8 fails
                content = file_path.read_text(encoding='latin-1')
                console.print("[yellow]Warning:[/yellow] File was not UTF-8 encoded, using Latin-1 encoding")
            except Exception as e:
                console.print(f"[bold red]Error reading file:[/bold red] {str(e)}")
                raise typer.Exit(code=EXIT_ERROR_GENERAL)
        
        # Parse URLs, skipping empty lines and removing whitespace
        urls = [url.strip() for url in content.splitlines() if url.strip()]
        
        if not urls:
            console.print(f"[bold yellow]Warning:[/bold yellow] No URLs found in {file}")
            raise typer.Exit(code=EXIT_ERROR_GENERAL)
        
        # Show initial progress information
        console.print(f"Found [blue]{len(urls)}[/blue] URLs in {file}")
        console.print(f"Processing with up to [blue]{max_concurrent}[/blue] concurrent tasks")
        console.print(f"Timeout per URL: [blue]{timeout}[/blue] seconds")
        console.print(f"All outputs will be saved to: [blue]{output_dir}[/blue]")
        console.print("Individual filenames will be auto-generated based on URLs")
        
        # Create progress display
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
            transient=not verbose,  # Keep progress visible in verbose mode
        ) as progress:
            task = progress.add_task(f"Processing {len(urls)} URLs...", total=None)
            
            # Process URLs
            results = asyncio.run(bulk_process_urls(
                urls=urls,
                output_dir=output_dir,
                preserve_styles=preserve_styles,
                max_concurrency=max_concurrent,
                timeout=timeout
            ))
            
            # Mark task as complete
            progress.update(task, completed=True, description="Processing complete")
        
        # Show summary results with detailed output
        success_count = sum(1 for r in results if r["success"])
        failure_count = len(results) - success_count
        
        # Create a summary panel
        console.print(Panel(
            f"[bold]Processing Summary[/bold]\n\n"
            f"Total URLs: [blue]{len(urls)}[/blue]\n"
            f"Successful: [green]{success_count}[/green]\n"
            f"Failed: [red]{failure_count}[/red]",
            title="Results",
            expand=False
        ))
        
        # Show successful URLs with their output paths
        if success_count > 0:
            console.print("\n[bold green]Successfully Processed URLs:[/bold green]")
            successful_table = Table(show_header=True)
            successful_table.add_column("URL", style="blue", no_wrap=True)
            successful_table.add_column("Output Path", style="green")
            successful_table.add_column("Processing Time", style="cyan")
            
            for result in results:
                if result["success"]:
                    time_str = f"{result.get('processing_time', 0):.2f}s" if "processing_time" in result else "N/A"
                    successful_table.add_row(
                        result["url"],
                        str(result["output_path"]),
                        time_str
                    )
            
            console.print(successful_table)
        
        # Show failed URLs with their error messages
        if failure_count > 0:
            console.print("\n[bold red]Failed URLs:[/bold red]")
            failed_table = Table(show_header=True)
            failed_table.add_column("URL", style="blue", no_wrap=True)
            failed_table.add_column("Error", style="red")
            
            for result in results:
                if not result["success"]:
                    failed_table.add_row(result["url"], result["error"])
            
            console.print(failed_table)
            
            # Return error code if ANY URLs fail
            raise typer.Exit(code=EXIT_ERROR_PROCESSING)
        
    except Exception as e:
        console.print(f"[bold red]Error processing URLs file:[/bold red] {str(e)}")
        raise


@app.command()
def version():
    """Show the current version of web2json."""
    version = __import__('web2json').__version__
    console.print(f"web2json version [bold]{version}[/bold]")


if __name__ == "__main__":
    app()
