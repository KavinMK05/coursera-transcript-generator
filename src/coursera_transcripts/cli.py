import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.theme import Theme

from .api import CourseAPI
from .downloader import TranscriptDownloader

# ── Custom theme ──────────────────────────────────────────────────────
custom_theme = Theme({
    "brand":    "bold bright_cyan",
    "accent":   "bright_magenta",
    "success":  "bold bright_green",
    "warning":  "bold yellow",
    "error":    "bold red",
    "muted":    "dim white",
    "info":     "bright_blue",
})

console = Console(theme=custom_theme)

BANNER = r"""[bright_cyan]
   ██████╗ ██████╗ ██╗   ██╗██████╗ ███████╗███████╗██████╗  █████╗
  ██╔════╝██╔═══██╗██║   ██║██╔══██╗██╔════╝██╔════╝██╔══██╗██╔══██╗
  ██║     ██║   ██║██║   ██║██████╔╝███████╗█████╗  ██████╔╝███████║
  ██║     ██║   ██║██║   ██║██╔══██╗╚════██║██╔══╝  ██╔══██╗██╔══██║
  ╚██████╗╚██████╔╝╚██████╔╝██║  ██║███████║███████╗██║  ██║██║  ██║
   ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
[/bright_cyan]"""


def _show_banner() -> None:
    console.print(BANNER)
    subtitle = Text("Transcript Generator", style="bold bright_magenta")
    subtitle.append("  •  ", style="dim")
    subtitle.append("v0.1.0", style="dim bright_cyan")
    console.print(subtitle, justify="center")
    console.print()


def _normalize_cookie(raw: str) -> str:
    """Accept a raw CAUTH token, CAUTH=value, or a full Cookie header string."""
    raw = raw.strip()
    if "CAUTH=" in raw:
        # Already contains the CAUTH key — treat as a full cookie string
        return raw
    # Bare token value — wrap it
    return f"CAUTH={raw}"


def _prompt_cookie() -> str:
    console.print(
        Panel(
            "[muted]Paste your [bold bright_cyan]Cookie[/bold bright_cyan] header or just the [bold bright_cyan]CAUTH[/bold bright_cyan] value.\n"
            "You can copy the full Cookie header from DevTools → Network → any request → Headers.[/muted]",
            title="[brand]🔑  Authentication[/brand]",
            border_style="bright_cyan",
            padding=(1, 2),
        )
    )
    cookie = Prompt.ask("[bright_cyan]  ›[/bright_cyan] [bold]Cookie / CAUTH[/bold]")
    if not cookie.strip():
        console.print("[error]  ✖  Cookie cannot be empty.[/error]")
        raise SystemExit(1)
    return _normalize_cookie(cookie)


def _prompt_slug() -> str:
    console.print()
    console.print(
        Panel(
            "[muted]Enter the course slug from the URL.\n"
            "Example: [bold bright_cyan]coursera.org/learn/[underline]unreal-engine-fundamentals[/underline][/bold bright_cyan][/muted]",
            title="[brand]📚  Course[/brand]",
            border_style="bright_cyan",
            padding=(1, 2),
        )
    )
    slug = Prompt.ask("[bright_cyan]  ›[/bright_cyan] [bold]Course slug[/bold]")
    if not slug.strip():
        console.print("[error]  ✖  Slug cannot be empty.[/error]")
        raise SystemExit(1)
    return slug.strip()


def _prompt_options() -> tuple[str, str, Path]:
    console.print()
    console.print(
        Panel(
            "[muted]Configure optional settings (press Enter for defaults).[/muted]",
            title="[brand]⚙  Options[/brand]",
            border_style="bright_cyan",
            padding=(1, 2),
        )
    )
    language = Prompt.ask(
        "[bright_cyan]  ›[/bright_cyan] [bold]Language[/bold]",
        default="en",
    )
    fmt = Prompt.ask(
        "[bright_cyan]  ›[/bright_cyan] [bold]Format[/bold] [muted](srt/txt)[/muted]",
        choices=["srt", "txt"],
        default="txt",
    )
    output = Prompt.ask(
        "[bright_cyan]  ›[/bright_cyan] [bold]Output directory[/bold]",
        default="./output",
    )
    return language, fmt, Path(output).resolve()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download transcripts/subtitles from a Coursera course",
    )
    parser.add_argument(
        "--cookie", "-c",
        help="Coursera authentication cookie (CAUTH value). If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--slug", "-s",
        help="Course slug (e.g. 'unreal-engine-fundamentals'). If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Parent output directory (default: ./output). Transcripts saved to {output}/{slug}/",
    )
    parser.add_argument(
        "--language", "-l",
        default=None,
        help="Subtitle language code (default: en)",
    )
    parser.add_argument(
        "--format",
        choices=["srt", "txt"],
        default=None,
        help="Subtitle format (default: txt)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # ── Interactive mode when cookie/slug not provided ────────────────
    interactive = args.cookie is None or args.slug is None

    if interactive:
        _show_banner()

    # Cookie
    if args.cookie:
        cookie = _normalize_cookie(args.cookie)
    else:
        cookie = _prompt_cookie()

    # Slug
    slug = args.slug if args.slug else _prompt_slug()

    # Options
    if interactive and (args.language is None and args.format is None and args.output is None):
        language, fmt, output_dir = _prompt_options()
    else:
        language = args.language or "en"
        fmt = args.format or "txt"
        output_dir = Path(args.output or "./output").resolve()

    console.print()

    # ── Run ───────────────────────────────────────────────────────────
    api = CourseAPI(cookie, console)
    downloader = TranscriptDownloader(
        api=api,
        output_dir=output_dir,
        language=language,
        fmt=fmt,
        console=console,
    )

    try:
        downloader.fetch_all_transcripts(slug)
    except ValueError as e:
        console.print(f"\n[error]  ✖  {e}[/error]")
        raise SystemExit(1)
    except KeyboardInterrupt:
        console.print("\n[warning]  ⚠  Interrupted by user.[/warning]")
        raise SystemExit(130)
    except Exception as e:
        console.print(f"\n[error]  ✖  Unexpected error: {e}[/error]")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
