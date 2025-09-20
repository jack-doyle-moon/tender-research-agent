"""Command-line interface for the research system."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import track
from rich.table import Table

from app.config import settings
from app.orchestrator import ResearchWorkflow

app = typer.Typer(help="Multi-Agent Research & Validation System")
console = Console()


@app.command()
def run(
    rfp_path: str = typer.Argument(..., help="Path to RFP document (PDF or DOCX)"),
    company: str = typer.Argument(..., help="Target company name"),
    max_iters: int = typer.Option(None, "--max-iters", help="Maximum refinement iterations"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory for results"),
) -> None:
    """Run the complete research and validation workflow."""
    
    console.print(f"[bold blue]Starting research workflow for {company}[/bold blue]")
    console.print(f"RFP: {rfp_path}")
    
    # Validate inputs
    rfp_file = Path(rfp_path)
    if not rfp_file.exists():
        console.print(f"[red]Error: RFP file not found: {rfp_path}[/red]")
        raise typer.Exit(1)
    
    if rfp_file.suffix.lower() not in ['.pdf', '.docx']:
        console.print(f"[red]Error: Unsupported file type: {rfp_file.suffix}[/red]")
        raise typer.Exit(1)
    
    # Run workflow
    workflow = ResearchWorkflow()
    
    with console.status("[bold green]Processing...") as status:
        try:
            result = workflow.run(
                rfp_path=str(rfp_file.absolute()),
                company_name=company,
                max_iterations=max_iters
            )
            
            console.print(f"[green]✓ Workflow completed[/green]")
            console.print(f"Run ID: {result['run_id']}")
            console.print(f"Iterations: {result['current_iteration']}")
            
            # Display summary
            if result.get('validation_report'):
                coverage = result['validation_report'].get('coverage_score', 0)
                console.print(f"Coverage Score: {coverage:.1%}")
            
            if result.get('errors'):
                console.print("[red]Errors encountered:[/red]")
                for error in result['errors']:
                    console.print(f"  • {error}")
            
            # Show output location
            run_dir = settings.data_dir / "runs" / result['run_id']
            console.print(f"[blue]Results saved to: {run_dir}[/blue]")
            
            # Copy to output directory if specified
            if output_dir:
                import shutil
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                
                if (run_dir / "outline.md").exists():
                    shutil.copy2(run_dir / "outline.md", output_path / "bid_outline.md")
                    console.print(f"[blue]Bid outline copied to: {output_path / 'bid_outline.md'}[/blue]")
            
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            raise typer.Exit(1)


@app.command()
def ingest(
    rfp_path: str = typer.Argument(..., help="Path to RFP document"),
    company: str = typer.Argument(..., help="Company name"),
) -> None:
    """Ingest and analyze RFP document."""
    
    console.print(f"[bold blue]Analyzing RFP: {rfp_path}[/bold blue]")
    
    rfp_file = Path(rfp_path)
    if not rfp_file.exists():
        console.print(f"[red]Error: File not found: {rfp_path}[/red]")
        raise typer.Exit(1)
    
    try:
        from app.tools import DocumentProcessor
        processor = DocumentProcessor()
        
        # Process document
        chunks = processor.process_document(rfp_file)
        metadata = processor.extract_metadata(rfp_file)
        
        console.print(f"[green]✓ Document processed[/green]")
        console.print(f"Pages/Sections: {metadata.get('pages', 'N/A')}")
        console.print(f"Chunks: {len(chunks)}")
        console.print(f"Total Characters: {sum(len(chunk.text) for chunk in chunks):,}")
        
        # Preview first chunk
        if chunks:
            console.print("\n[bold]Preview:[/bold]")
            preview = chunks[0].text[:200] + "..." if len(chunks[0].text) > 200 else chunks[0].text
            console.print(preview)
        
    except Exception as e:
        console.print(f"[red]Error processing document: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def report(
    run_id: Optional[str] = typer.Option(None, help="Specific run ID to report on"),
    latest: bool = typer.Option(False, "--latest", help="Report on latest run"),
    list_runs: bool = typer.Option(False, "--list", help="List all runs"),
) -> None:
    """Generate reports from previous runs."""
    
    runs_dir = settings.data_dir / "runs"
    
    if list_runs:
        console.print("[bold blue]Available Runs:[/bold blue]")
        
        if not runs_dir.exists():
            console.print("No runs found.")
            return
        
        table = Table()
        table.add_column("Run ID")
        table.add_column("Company")
        table.add_column("Coverage")
        table.add_column("Requirements")
        table.add_column("Evidence")
        table.add_column("Status")
        table.add_column("Timestamp")
        
        for run_dir in sorted(runs_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if run_dir.is_dir():
                summary_file = run_dir / "summary.json"
                inputs_file = run_dir / "inputs.json"
                
                if summary_file.exists() and inputs_file.exists():
                    with open(summary_file) as f:
                        summary = json.load(f)
                    with open(inputs_file) as f:
                        inputs = json.load(f)
                    
                    status = "✓ Complete" if summary.get('is_complete') else "⚠ Incomplete"
                    if summary.get('errors'):
                        status = "✗ Error"
                    
                    table.add_row(
                        run_dir.name[:8] + "...",
                        inputs.get('company_name', 'Unknown'),
                        f"{summary.get('coverage_score', 0):.1%}",
                        str(summary.get('requirements_count', 0)),
                        str(summary.get('evidence_count', 0)),
                        status,
                        summary.get('timestamp', '')[:10]
                    )
        
        console.print(table)
        return
    
    # Find target run
    target_run_id = None
    if run_id:
        target_run_id = run_id
    elif latest:
        # Find latest run
        if runs_dir.exists():
            run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
            if run_dirs:
                latest_dir = max(run_dirs, key=lambda x: x.stat().st_mtime)
                target_run_id = latest_dir.name
    
    if not target_run_id:
        console.print("[red]No run specified. Use --run-id, --latest, or --list[/red]")
        raise typer.Exit(1)
    
    # Generate report
    run_dir = runs_dir / target_run_id
    if not run_dir.exists():
        console.print(f"[red]Run not found: {target_run_id}[/red]")
        raise typer.Exit(1)
    
    try:
        # Load run data
        with open(run_dir / "summary.json") as f:
            summary = json.load(f)
        with open(run_dir / "inputs.json") as f:
            inputs = json.load(f)
        
        console.print(f"[bold blue]Run Report: {target_run_id}[/bold blue]")
        console.print(f"Company: {inputs.get('company_name')}")
        console.print(f"RFP: {Path(inputs.get('rfp_path', '')).name}")
        console.print(f"Timestamp: {summary.get('timestamp')}")
        console.print(f"Iterations: {summary.get('iterations')}")
        console.print(f"Status: {'Complete' if summary.get('is_complete') else 'Incomplete'}")
        
        # Coverage details
        console.print(f"\n[bold]Coverage Analysis:[/bold]")
        console.print(f"Overall Score: {summary.get('coverage_score', 0):.1%}")
        console.print(f"Requirements Found: {summary.get('requirements_count', 0)}")
        console.print(f"Evidence Sources: {summary.get('evidence_count', 0)}")
        
        # Load detailed validation if available
        validation_file = run_dir / "validation.json"
        if validation_file.exists():
            with open(validation_file) as f:
                validation = json.load(f)
            
            gaps = validation.get('gaps', [])
            if gaps:
                console.print(f"\n[bold]Gaps Identified ({len(gaps)}):[/bold]")
                for gap in gaps[:5]:  # Show top 5
                    console.print(f"  • {gap.get('requirement_id')}: {gap.get('why')}")
        
        # Errors
        if summary.get('errors'):
            console.print(f"\n[bold red]Errors:[/bold red]")
            for error in summary['errors']:
                console.print(f"  • {error}")
        
        console.print(f"\n[blue]Full results available in: {run_dir}[/blue]")
        
    except Exception as e:
        console.print(f"[red]Error generating report: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def config() -> None:
    """Show current configuration."""
    console.print("[bold blue]Configuration:[/bold blue]")
    console.print(f"Data Directory: {settings.data_dir}")
    console.print(f"OpenAI Model: {settings.openai_model}")
    console.print(f"Max Iterations: {settings.max_iterations}")
    console.print(f"Cache TTL: {settings.cache_ttl_hours}h")
    console.print(f"PII Redaction: {'Enabled' if settings.enable_pii_redaction else 'Disabled'}")
    
    # Check API keys
    console.print(f"\n[bold]API Keys:[/bold]")
    console.print(f"OpenAI: {'✓ Set' if settings.openai_api_key else '✗ Missing'}")
    console.print(f"SerpAPI: {'✓ Set' if settings.serpapi_api_key else '✗ Not set'}")
    console.print(f"Tavily: {'✓ Set' if settings.tavily_api_key else '✗ Not set'}")


if __name__ == "__main__":
    app()
